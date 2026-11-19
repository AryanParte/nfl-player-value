"""Independent moment identities and separation/accounting regression checks."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scipy.special import logsumexp, roots_hermitenorm
from scipy.stats import multivariate_normal

from nfl_value.control_variates import (
    FittedControl,
    GaussianControls,
    controlled_integrals,
    fit_control,
    integrate_controlled,
    training_points,
)
from nfl_value.coarse_control_study import (
    authorize,
    load,
    plain_reference,
    save,
    validate_archive,
    validate_fit,
    validate_plan,
)
from nfl_value.ingestion import SnapshotStore, json_bytes, sha256
from nfl_value.density_holdout import StabilizedProposal
from nfl_value.two_level_reference import sampling_hash
from nfl_value.replicated_reference import (
    diagnose_reference,
    replicate_integrals,
    summarize_integrals,
)


class GaussianMixture:
    mean = np.zeros(2)

    def __init__(self, coincident=False):
        self.coincident = coincident

    def components(self, method):
        covariance = np.array([[1.0, 0.25], [0.25, 0.8]])
        return [
            (mass, np.array([m, -m]), covariance, None)
            for mass, m in zip(
                [0.1, 0.2, 0.3, 0.4], [0] * 4 if self.coincident else [-0.4, 0, 0.2, 0.5]
            )
        ]

    def logpdf(self, points, method):
        return logsumexp(
            [
                np.log(m) + multivariate_normal.logpdf(points, mean=mu, cov=cov)
                for m, mu, cov, _ in self.components(method)
            ],
            axis=0,
        )


def plan():
    return json.loads(Path("config/coarse-control-v1.json").read_text())


class ControlVariateTests(unittest.TestCase):
    def test_saved_archive_recomputes_both_references_and_all_work(self):
        p = plan()
        geometry = dict(
            pilot_initial_geometry=dict(mode=[0.0, 0.0], covariance=np.eye(2).tolist()),
            component_means=np.zeros((3, 2)).tolist(),
            component_covariances=np.tile(np.eye(2), (3, 1, 1)).tolist(),
            component_masses=[0.2, 0.3, 0.5],
            geometry_uses_primary_qmc=False,
            learning_is_target_density_only=True,
        )
        sampling = StabilizedProposal(
            np.zeros(2),
            np.eye(2),
            np.zeros(2),
            np.eye(2),
            geometry,
            np.zeros((3, 2)),
            np.tile(np.eye(2), (3, 1, 1)),
            np.array([0.2, 0.3, 0.5]),
        )
        raw = np.tile([1, 0, 0.025, 0.975], (p["replicates"], 1))
        entropy = [p["base_seed"], 1, 0, 0]
        fit = fit_control(
            lambda x, q: np.tile(raw[0], (len(x), 1)),
            sampling,
            entropy=[*entropy, 2],
            nodes=p["training_nodes"],
            relative_ridge=p["relative_ridge"],
        ).record()
        reference = summarize_integrals(
            raw, {0.0: {"mean": np.zeros(1)}}, p, sampling, "stabilized-mixture"
        )
        record = dict(
            status="complete",
            numerical_valid=True,
            primary_qmc_valid=True,
            entropy=entropy,
            coarse=raw.tolist(),
            plain_coarse=raw.tolist(),
            correction=np.zeros_like(raw).tolist(),
            fit=fit,
            reference=reference,
            geometry_sha256=sha256(json_bytes(geometry)),
            sampling_sha256=sampling_hash(sampling),
            contrasts=1,
            shifts=[0.0],
            diagnosis=diagnose_reference(reference, contrasts=1, shifts=[0.0], plan=p),
            plain_reference=plain_reference(raw, 1, [0.0], p, sampling),
            evaluations=dict(fine=2049, coarse=71680),
        )
        cases = {
            name: dict(status="unattempted", numerical_valid=False, error="bounded test")
            for name in p["cases"]
        }
        cases["real_evolving"] = record
        result = dict(
            plan=p,
            cases=cases,
            model_plan=dict(log_precision_mean=0.0, log_precision_sd=1.0),
            nfl_data_used=True,
            calibration_completed=False,
            ranking_ready=False,
            numerical_pilot_passed=False,
        )
        validate_archive(result)
        for change in ["fit", "plain", "bounds", "work", "omit", "admit"]:
            bad = deepcopy(result)
            r = bad["cases"]["real_evolving"]
            if change == "fit":
                r["fit"]["coefficients"][0][0] += 1
            elif change == "plain":
                r["plain_coarse"][0][0] += 1
            elif change == "bounds":
                r["reference"]["bounds"]["low"][1] -= 1
            elif change == "work":
                r["evaluations"]["coarse"] -= p["training_nodes"]
            elif change == "omit":
                bad["cases"].pop("real_team")
            else:
                bad["numerical_pilot_passed"] = True
            with self.assertRaises(ValueError):
                validate_archive(bad)

    def test_case_storage_retains_cap_and_rejects_corruption(self):
        result = dict(
            experiment="coarse-control-controls-v1",
            plan=plan(),
            cases=[dict(target=i, payload=str(i) * 10000) for i in range(5)],
        )
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("nfl_value.ingestion.MAX_DOWNLOAD_BYTES", 20000),
            patch("nfl_value.coarse_control_study.validate_known"),
        ):
            store = SnapshotStore(directory)
            rid, manifest = save(store, result, "a" * 40)
            self.assertEqual(json_bytes(load(store, rid)[1]), json_bytes(result))
            index = json.loads(store.read(manifest["objects"]["study"]))
            self.assertEqual(len(index["cases"]), 5)
            self.assertTrue(
                all(p.stat().st_size <= 20000 for p in (store.root / "objects").iterdir())
            )
            (store.root / "objects" / index["cases"][0][1]).write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                load(store, rid)

    def test_all_zero_means_by_independent_gaussian_mixture_quadrature(self):
        sampling = GaussianMixture()
        basis = GaussianControls(sampling)
        nodes, weights = roots_hermitenorm(48)
        grid = np.stack(np.meshgrid(nodes, nodes, indexing="ij"), axis=-1).reshape(-1, 2)
        weights = np.outer(weights, weights).ravel() / (2 * np.pi)
        answer = np.zeros(basis.width)
        for mass, mean, covariance, _ in sampling.components("stabilized-mixture"):
            x = mean + grid @ np.linalg.cholesky(covariance).T
            answer += mass * (weights @ basis.features(x, sampling.logpdf(x, "stabilized-mixture")))
        np.testing.assert_allclose(answer, 0, rtol=0, atol=2e-12)
        # In one exactly matching Gaussian, the independent standard coordinates
        # give the Hermite basis directly, including off-diagonal covariance.
        same = GaussianMixture(coincident=True)
        x = grid @ np.linalg.cholesky(same.components("")[0][2]).T
        h = GaussianControls(same).features(x, same.logpdf(x, ""))
        truth = np.column_stack(
            [
                np.zeros(len(grid)),
                grid[:, 0],
                grid[:, 1],
                grid[:, 0] ** 2 - 1,
                grid[:, 0] * grid[:, 1],
                grid[:, 1] ** 2 - 1,
            ]
        )
        np.testing.assert_allclose(h[:, :6], truth, rtol=1e-12, atol=1e-10)

    def test_exact_signed_integrals_and_paired_plain_values(self):
        sampling = GaussianMixture()
        basis = GaussianControls(sampling)
        coefficients = np.arange(basis.width * 3).reshape(basis.width, 3) / 100
        constant = np.array([2.0, -4.0, 0.0])
        f = lambda x, q: constant + basis.features(x, q) @ coefficients
        fitted = FittedControl(basis, coefficients, {})
        adjusted, plain = controlled_integrals(
            f, fitted, sampling, entropy=[1616, 0], replicates=8, nodes=128
        )
        np.testing.assert_allclose(adjusted, np.tile(constant, (8, 1)), atol=2e-14)
        reference = replicate_integrals(
            f, sampling, "stabilized-mixture", entropy=[1616, 0], replicates=8, nodes=128
        )
        np.testing.assert_array_equal(plain, reference)
        self.assertTrue((adjusted[:, 1] < 0).all())

    def test_independent_training_weighting_collinearity_and_frozen_coefficients(self):
        sampling = GaussianMixture(coincident=True)
        basis = GaussianControls(sampling)
        seen = []

        def f(x, q):
            seen.append(x.copy())
            return np.column_stack([np.ones(len(x)), -3 + basis.features(x, q)[:, 1]])

        fitted = fit_control(f, sampling, entropy=[1616, 2], nodes=512, relative_ridge=1e-6)
        points, weights = training_points(sampling, [1616, 2], 512)
        np.testing.assert_array_equal(points, seen[0])
        np.testing.assert_allclose(weights.reshape(4, 128).sum(axis=1), [0.1, 0.2, 0.3, 0.4])
        self.assertLess(fitted.diagnostics["numerical_rank"], basis.width)
        before = fitted.coefficients.copy()
        a, _ = controlled_integrals(f, fitted, sampling, entropy=[1616, 0], replicates=8, nodes=128)
        np.testing.assert_array_equal(before, fitted.coefficients)
        self.assertFalse(any(np.array_equal(block, seen[0][: len(block)]) for block in seen[1:]))
        np.testing.assert_allclose(a.mean(axis=0), [1, -3], atol=1e-6)
        repeat = fit_control(f, sampling, entropy=[1616, 2], nodes=512, relative_ridge=1e-6)
        self.assertEqual(json_bytes(fitted.record()), json_bytes(repeat.record()))

    def test_two_levels_preserve_correction_and_complete_work(self):
        sampling = GaussianMixture()
        calls = {"fine": 0, "coarse": 0}

        def fine(x, q):
            calls["fine"] += len(x)
            return np.tile([2, -6, 0], (len(x), 1))

        def coarse(x, q):
            calls["coarse"] += len(x)
            return np.tile([8, 24, -1], (len(x), 1))

        p = {
            **plan(),
            "replicates": 4,
            "nodes_per_replicate": 64,
            "correction_nodes_per_replicate": 16,
            "training_nodes": 128,
        }
        out = integrate_controlled(fine, coarse, sampling, entropy=[1616, 3], plan=p)
        np.testing.assert_allclose(out["total"], np.tile([2, -6, 0], (4, 1)), atol=1e-13)
        self.assertEqual(calls, {"fine": 64, "coarse": 448})
        self.assertEqual(out["fit"]["training_entropy"], [1616, 3, 2])

    def test_invalid_fit_and_response_mismatch_fail_without_clipping(self):
        sampling = GaussianMixture()
        for nodes in [0, 3, True, 16.0]:
            with self.assertRaises(ValueError):
                training_points(sampling, [1], nodes)
        with self.assertRaisesRegex(ValueError, "training responses"):
            fit_control(
                lambda x, q: np.full((len(x), 1), np.nan),
                sampling,
                entropy=[2],
                nodes=64,
                relative_ridge=1e-6,
            )
        fitted = FittedControl(GaussianControls(sampling), np.ones((24, 2)), {})
        with self.assertRaisesRegex(ValueError, "dimensions"):
            controlled_integrals(
                lambda x, q: np.ones((len(x), 1)),
                fitted,
                sampling,
                entropy=[3],
                replicates=4,
                nodes=64,
            )
        bad = FittedControl(fitted.basis, np.full((24, 1), 1e3), {})
        negative, _ = controlled_integrals(
            lambda x, q: np.zeros((len(x), 1)), bad, sampling, entropy=[4], replicates=4, nodes=64
        )
        self.assertTrue(np.any(negative < 0))

    def test_fixed_plan_fit_binding_and_false_authorization(self):
        p = plan()
        validate_plan(p)
        for key in ["base_seed", "training_nodes", "reference_mean_tolerance_sd", "relative_ridge"]:
            with self.assertRaises(ValueError):
                validate_plan({**p, key: p[key] * 2})
        sampling = GaussianMixture()
        fit = fit_control(
            lambda x, q: np.ones((len(x), 2)),
            sampling,
            entropy=[p["base_seed"], 0, 0, 0, 2],
            nodes=p["training_nodes"],
            relative_ridge=p["relative_ridge"],
        ).record()
        validate_fit(fit, sampling, fit["training_entropy"], p, 2)
        for field in ["training_entropy", "coefficients", "training_nodes", "sampling_sha256"]:
            bad = deepcopy(fit)
            if field == "coefficients":
                bad[field][0][0] += 1
            elif field == "training_entropy":
                bad[field][-1] += 1
            elif field == "training_nodes":
                bad[field] -= 1
            else:
                bad[field] = "0" * 64
            with self.assertRaises(ValueError):
                validate_fit(bad, sampling, fit["training_entropy"], p, 2)
        result = dict(experiment="coarse-control-controls-v1", plan=p, controls_passed=False)
        with tempfile.TemporaryDirectory() as directory:
            store = SnapshotStore(directory)
            rid, manifest = save(store, result, "a" * 40)
            with patch("nfl_value.coarse_control_study.validate_known", return_value=False):
                with self.assertRaisesRegex(ValueError, "before NFL"):
                    authorize(store, rid)
            manifest["kernel_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "statistical code"):
                load(store, store.put(json_bytes(manifest), manifest=True))
            self.assertEqual(fit["coefficients_sha256"], sha256(json_bytes(fit["coefficients"])))


if __name__ == "__main__":
    unittest.main()
