"""Retrospective observed QB/target-mix transitions, never causal absences or CAVAA."""

from collections import Counter, defaultdict
from math import fsum

from nfl_value.baseline import GROUPS, actor_features, prepare_plays
from nfl_value.ingestion import json_bytes, sha256
from nfl_value.source_audit import aware_time


PLAN = {
    "plan_version": 1,
    "evaluation_labels": ["historical_test", "transfer_test"],
    "minimum_team_dropbacks": 10,
    "minimum_leader_share": 0.75,
    "high_target_mix_change": 0.5,
    "any_actor_issue_blocks_case": True,
    "require_complete_ledger_context": True,
    "adjacency": "consecutive-completed-team-games-within-evaluation",
    "prediction_models": ["joint", "role"],
    "actor_penalty": 1000.0,
    "uncertainty": "leave-one-offense-team-out-sensitivity-not-confidence-interval",
}


def validate_plan(plan):
    # Type-strict equality also rejects true in place of a numeric one.
    if json_bytes(plan) != json_bytes(PLAN):
        raise ValueError("unsupported transition plan; use the frozen version")


def target_mix_distance(previous, current):
    """Total variation of recorded target shares, not lineup quality."""
    if not previous or not current:
        return None
    a, b = sum(previous.values()), sum(current.values())
    if a <= 0 or b <= 0:
        return None
    return 0.5 * fsum(
        abs(previous.get(p, 0) / a - current.get(p, 0) / b)
        for p in sorted(previous.keys() | current.keys())
    )


def panel(game, raw_rows, rows, predictions, roster):
    reasons = []
    if not rows or len(raw_rows) != len(rows):
        reasons.append("incomplete_ledger_context_or_empty_model_rows")
    if any(p["issues"] or p["event_kind"] in {"aborted", "unclassified"} for p in raw_rows):
        reasons.append("actor_issue_or_ambiguous_event")
    dropbacks, quarterbacks, targets = Counter(), Counter(), Counter()
    for play in rows:
        actors = actor_features(play)
        links = [name.split("/")[1] for name in actors if name.startswith("dropback/")]
        if play["event_kind"] in {"pass", "sack", "scramble"} and not links:
            reasons.append("missing_dropback_identity")
        for player in links:
            dropbacks[player] += 1
            observation = roster.get((player, game.game_id, game.team_id))
            if (
                not observation
                or observation["issues"]
                or observation["source_position_role"] is None
            ):
                reasons.append("unresolved_dropback_position_or_identity")
            elif observation["source_position_role"] == "QB":
                quarterbacks[player] += 1
        targets.update(name.split("/")[1] for name in actors if name.startswith("target/"))
    total = sum(dropbacks.values())
    if total < PLAN["minimum_team_dropbacks"]:
        reasons.append("too_few_observed_dropbacks")
    leaders = [p for p, count in quarterbacks.items() if count == max(quarterbacks.values())]
    leader = leaders[0] if len(leaders) == 1 else None
    if leader is None:
        reasons.append("no_unique_qb_leader")
    elif quarterbacks[leader] / total < PLAN["minimum_leader_share"]:
        reasons.append("qb_leader_share_below_minimum")
    means = {}
    if rows:
        for variant, pred in predictions.items():
            means[variant] = {
                "predicted_epa_per_play": fsum(p["predicted_epa"] for p in pred) / len(rows),
                "components_epa_per_play": {
                    group: fsum(p["components"][group] for p in pred) / len(rows)
                    for group in GROUPS
                },
                "residual_epa_per_play": fsum(p["residual"] for p in pred) / len(rows),
            }
    return {
        "game_id": game.game_id,
        "team": game.team_id,
        "kickoff": game.kickoff.isoformat(),
        "week": int(game.game_id.split("_")[1]),
        "ledger_plays": len(raw_rows),
        "modeled_plays": len(rows),
        "dropbacks_by_player": dict(sorted(dropbacks.items())),
        "recorded_targets_by_player": dict(sorted(targets.items())),
        "observed_qb_leader": leader,
        "leader_dropback_share": quarterbacks[leader] / total if leader else None,
        "observed_epa_per_play": fsum(p["offense_epa"] for p in rows) / len(rows) if rows else None,
        "models": means,
        "case_eligible": not reasons,
        "blocked_reasons": sorted(set(reasons)),
        "injury_absence_verified": False,
    }


def case(previous, current, *, coefficients, training_counts, roster):
    old, new = previous["observed_qb_leader"], current["observed_qb_leader"]
    mix = target_mix_distance(
        previous["recorded_targets_by_player"], current["recorded_targets_by_player"]
    )
    changed = old != new
    groups = ["all", "qb_changed" if changed else "qb_retained"]
    if changed:
        groups.append(
            "qb_changed_prior_not_observed"
            if current["dropbacks_by_player"].get(old, 0) == 0
            else "qb_changed_prior_still_observed"
        )
    else:
        groups.append(
            "qb_retained_target_mix_unknown"
            if mix is None
            else "qb_retained_target_mix_high"
            if mix >= PLAN["high_target_mix_change"]
            else "qb_retained_target_mix_low"
        )
    observed = current["observed_epa_per_play"] - previous["observed_epa_per_play"]
    model_changes = {}
    for variant in PLAN["prediction_models"]:
        prediction = (
            current["models"][variant]["predicted_epa_per_play"]
            - previous["models"][variant]["predicted_epa_per_play"]
        )
        model_changes[variant] = {
            "predicted_change_epa_per_play": prediction,
            "prediction_minus_observed_change": prediction - observed,
            "absolute_change_error": abs(prediction - observed),
        }
    components = {
        group: current["models"]["joint"]["components_epa_per_play"][group]
        - previous["models"]["joint"]["components_epa_per_play"][group]
        for group in GROUPS
    }
    components["residual"] = (
        current["models"]["joint"]["residual_epa_per_play"]
        - previous["models"]["joint"]["residual_epa_per_play"]
    )
    accounting_error = abs(fsum(components.values()) - observed)
    if accounting_error > 1e-9:
        raise ValueError("transition component accounting failed")
    swap = None
    if changed:
        old_feature, new_feature = f"dropback/{old}", f"dropback/{new}"
        missing = [
            n for n in (old_feature, new_feature) if not training_counts[n] or n not in coefficients
        ]
        n = current["dropbacks_by_player"][new]
        swap = {
            "current_leader_dropbacks": n,
            "new_minus_prior_on_current_dropbacks_ep": None
            if missing
            else n * (coefficients[new_feature] - coefficients[old_feature]),
            "untrained_features": missing,
            "training_dropbacks": {n: training_counts[n] for n in (old_feature, new_feature)},
            "benchmark": "previous_observed_qb_not_cavaa_first_unit",
        }
    observation = roster.get((old, current["game_id"], current["team"]))
    return {
        "previous_game_id": previous["game_id"],
        "current_game_id": current["game_id"],
        "team": current["team"],
        "previous_leader": old,
        "current_leader": new,
        "groups": groups,
        "target_mix_total_variation": mix,
        "previous_leader_current_dropbacks": current["dropbacks_by_player"].get(old, 0),
        "previous_leader_current_roster": {
            "record_present": observation is not None,
            "source_position_role": observation["source_position_role"] if observation else None,
            "observed_offensive_participation": observation["observed_offensive_participation"]
            if observation
            else None,
            "issues": observation["issues"] if observation else ["no_roster_game_record"],
        },
        "observed_change_epa_per_play": observed,
        "models": model_changes,
        "joint_component_changes_epa_per_play": components,
        "accounting_error": accounting_error,
        "identity_swap_diagnostic": swap,
        "injury_absence_verified": False,
        "causal_effect_estimated": False,
    }


CASE_GROUPS = (
    "all",
    "qb_changed",
    "qb_retained",
    "qb_changed_prior_not_observed",
    "qb_changed_prior_still_observed",
    "qb_retained_target_mix_high",
    "qb_retained_target_mix_low",
    "qb_retained_target_mix_unknown",
)


def summarize(cases):
    teams = sorted({c["team"] for c in cases})
    differences = [
        (
            c["team"],
            c["models"]["joint"]["absolute_change_error"]
            - c["models"]["role"]["absolute_change_error"],
        )
        for c in cases
    ]
    leave_out = (
        [
            fsum(v for team, v in differences if team != omitted)
            / sum(team != omitted for team, _ in differences)
            for omitted in teams
        ]
        if len(teams) > 1
        else []
    )
    return {
        "pairs": len(cases),
        "offense_teams": len(teams),
        "distinct_games": len(
            {g for c in cases for g in (c["previous_game_id"], c["current_game_id"])}
        ),
        "mean_absolute_change_error": {
            variant: fsum(c["models"][variant]["absolute_change_error"] for c in cases) / len(cases)
            if cases
            else None
            for variant in PLAN["prediction_models"]
        },
        "joint_minus_role_mae": fsum(v for _, v in differences) / len(cases) if cases else None,
        "leave_one_offense_team_out_range": [min(leave_out), max(leave_out)] if leave_out else None,
        "range_is_confidence_interval": False,
        "max_component_accounting_error": max((c["accounting_error"] for c in cases), default=None),
    }


def experiment(ledgers, evidence, games, baseline, models, predictions, *, plan):
    validate_plan(plan)
    if baseline["selected_actor_penalty"] != plan["actor_penalty"]:
        raise ValueError("transition audit cannot change the selected penalty")
    historical = ledgers["historical_test"]
    training_ids = set(models["joint"]["training_games"])
    training, _ = prepare_plays(
        {**historical, "plays": [p for p in historical["plays"] if p["game_id"] in training_ids]},
        season=historical["provenance"]["season"],
    )
    if {p["game_id"] for p in training} != training_ids:
        raise ValueError("missing training game evidence")
    training_hash = sha256(json_bytes({"plays": training}))
    for variant in plan["prediction_models"]:
        if (
            models[variant]["training_rows_sha256"] != training_hash
            or set(models[variant]["training_games"]) != training_ids
            or models[variant]["actor_penalty"] != plan["actor_penalty"]
        ):
            raise ValueError("model training cohort or penalty differs")
    last_training = max(aware_time(p["scheduled_kickoff"]) for p in training)
    training_counts = Counter(n for p in training for n in actor_features(p))
    coefficients = dict(
        zip(models["joint"]["features"], models["joint"]["coefficients"], strict=True)
    )
    panels, outputs, summaries = {}, {}, {}
    for label in plan["evaluation_labels"]:
        ids = set(baseline["split_games"][label])
        if ids & training_ids or not ids:
            raise ValueError("empty or overlapping evaluation partition")
        completed_ids = {g.game_id for g in games[label]}
        expected_ids = completed_ids - training_ids if label == "historical_test" else completed_ids
        if ids != expected_ids or (
            label == "historical_test" and not training_ids <= completed_ids
        ):
            # An omitted completed game is not a bye. Do not bridge it even if
            # the saved partition contains no modeled rows for that game.
            raise ValueError("evaluation partition and completed game inventory differ")
        ledger = ledgers[label]
        raw_rows = [p for p in ledger["plays"] if p["game_id"] in ids]
        rows, preparation = prepare_plays(
            {**ledger, "plays": raw_rows}, season=ledger["provenance"]["season"]
        )
        if {p["game_id"] for p in rows} != ids or any(
            aware_time(p["scheduled_kickoff"]) <= last_training for p in raw_rows
        ):
            raise ValueError("incomplete evaluation or training/future leakage")
        inventory = {(g.game_id, g.team_id): g for g in games[label] if g.game_id in ids}
        if len(inventory) != 2 * len(ids) or len(inventory) != sum(
            g.game_id in ids for g in games[label]
        ):
            raise ValueError("incomplete or duplicate evaluation team-game inventory")
        for p in raw_rows:
            game = inventory.get((p["game_id"], p["offense_team"]))
            if game is None or game.kickoff != aware_time(p["scheduled_kickoff"]):
                raise ValueError("evaluation play outside completed game inventory")
        roster = {}
        for row in evidence[label]["player_games"]:
            if row["game_id"] not in ids:
                continue
            key = (row["player_id"], row["game_id"], row["team"])
            if key in roster:
                raise ValueError("duplicate roster player/game/team evidence")
            roster[key] = row
        raw_by_game, by_game = defaultdict(list), defaultdict(list)
        for p in raw_rows:
            raw_by_game[(p["game_id"], p["offense_team"])].append(p)
        for p in rows:
            by_game[(p["game_id"], p["offense_team"])].append(p)
        prediction_groups = {}
        for variant in plan["prediction_models"]:
            pred = predictions[label][variant]
            keys = [(p["game_id"], p["play_id"], p["offense_team"], p["offense_epa"]) for p in rows]
            if keys != [
                (p["game_id"], p["play_id"], p["offense_team"], p["observed_epa"]) for p in pred
            ]:
                raise ValueError("prediction and evaluation rows differ")
            prediction_groups[variant] = defaultdict(list)
            for p in pred:
                prediction_groups[variant][(p["game_id"], p["offense_team"])].append(p)
        selected = [
            panel(
                g,
                raw_by_game[key],
                by_game[key],
                {v: prediction_groups[v][key] for v in plan["prediction_models"]},
                roster,
            )
            for key, g in sorted(inventory.items(), key=lambda item: (item[1].kickoff, item[0]))
        ]
        previous, cases, excluded = {}, [], []
        for current in selected:
            old = previous.get(current["team"])
            previous[current["team"]] = current  # A bad game still breaks adjacency.
            if old is None:
                continue
            if aware_time(old["kickoff"]) >= aware_time(current["kickoff"]):
                raise ValueError("team games overlap in the transition sequence")
            if not old["case_eligible"] or not current["case_eligible"]:
                excluded.append(
                    {
                        "team": current["team"],
                        "previous_game_id": old["game_id"],
                        "current_game_id": current["game_id"],
                        "previous_reasons": old["blocked_reasons"],
                        "current_reasons": current["blocked_reasons"],
                    }
                )
                continue
            cases.append(
                case(
                    old,
                    current,
                    coefficients=coefficients,
                    training_counts=training_counts,
                    roster=roster,
                )
            )
        summaries[label] = {
            "completed_team_games": len(selected),
            "eligible_team_games": sum(p["case_eligible"] for p in selected),
            "adjacent_pairs": len(cases) + len(excluded),
            "excluded_pairs": len(excluded),
            "panel_issue_counts": dict(
                sorted(Counter(reason for p in selected for reason in p["blocked_reasons"]).items())
            ),
            "groups": {g: summarize([c for c in cases if g in c["groups"]]) for g in CASE_GROUPS},
            "identity_swaps_with_training_support": sum(
                c["identity_swap_diagnostic"] is not None
                and not c["identity_swap_diagnostic"]["untrained_features"]
                for c in cases
            ),
        }
        panels[label] = {"preparation": preparation, "team_games": selected}
        outputs[label] = {"cases": cases, "excluded_pairs": excluded}
    report = {
        "experiment_kind": "observed-lineup-transitions",
        "experiment_version": 1,
        "plan": plan,
        "summary": summaries,
        "ranking_ready": False,
        "individual_attribution_validated": False,
        "injury_absences_verified": False,
        "evidence_interpretation": "retrospective diagnostics on previously examined evaluation games",
    }
    return report, panels, outputs
