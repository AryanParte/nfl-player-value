import { z } from "zod";

export const ROLES = ["IDL", "EDGE", "LB", "CB", "S"] as const;
const role = z.enum(ROLES);
const count = z.number().int().nonnegative();
const credit = z.number().nonnegative().multipleOf(0.5);
const team = z.string().regex(/^[A-Z]{2,3}$/);
const game = z.string().regex(/^\d{4}_\d{2}_[A-Z]{2,3}_[A-Z]{2,3}$/);
const hash = z.string().regex(/^[0-9a-f]{64}$/);
const playerId = z.string().regex(/^00-\d{7}$/);
const time = z
  .string()
  .refine(
    (s) => /(?:Z|[+-]\d{2}:\d{2})$/.test(s) && Number.isFinite(Date.parse(s)),
    "Timezone-aware time required",
  );
const gameRow = z
  .object({
    game_id: game,
    week: z.number().int().min(1).max(18),
    team,
    opponent: team,
    chart_roles: z.array(role),
    sack_credits: credit,
    interceptions: count,
  })
  .strict();
const player = z
  .object({
    player_id: playerId,
    name: z.string().min(1).max(120).nullable(),
    teams: z.array(team).min(1),
    roles: z.array(role),
    chart_games: count,
    event_games: count,
    sack_credits: credit,
    interceptions: count,
    cavaa: z.null(),
    defensive_snaps: z.null(),
    games: z.array(gameRow).min(1),
  })
  .strict();
const provenance = z
  .object({
    offensive_report: hash,
    source_receipts: z
      .object({ pbp: hash, schedules: hash, depth_charts: hash, rosters: hash })
      .strict(),
    sources: z
      .array(
        z
          .object({
            kind: z.enum(["pbp", "schedules", "depth_charts", "rosters"]),
            fetched_at: time,
            updated_at: time,
            source_url: z.url().refine((s) => s.startsWith("https://")),
            license_id: z.literal("CC-BY-4.0"),
            license_url: z.url().refine((s) => s.startsWith("https://")),
            attribution: z.string().min(1),
          })
          .strict(),
      )
      .length(4),
    opportunity_policy: z.literal("observed-offensive-pass-run-v1"),
    chart_policy: z.literal("espn-formation-slots-2025-v1"),
    retrospective_chart_team_games: count,
    name_policy: z.string().min(1),
  })
  .strict();
const metrics = z
  .object({ sacks: z.number().nonnegative(), interceptions: count })
  .strict();
export const ExplorerSchema = z
  .object({
    schema_version: z.literal(1),
    kind: z.literal("defense_explorer"),
    data_mode: z.enum(["observed", "synthetic"]),
    ranking_ready: z.literal(false),
    season: z.number().int().min(2025).max(2100),
    cutoff: time,
    code_revision: z.string().regex(/^[0-9a-f]{40}$/),
    provenance,
    scope: z.string().min(1),
    coverage: z
      .object({
        completed_games: count.positive(),
        through_week: z.number().int().min(1).max(18),
        included_plays: count.positive(),
        players: count,
        expected_role_cells: count.positive(),
        role_cells: z
          .array(
            z
              .object({ role, complete_cells: count, blocked_cells: count })
              .strict(),
          )
          .length(5),
      })
      .strict(),
    players: z.array(player),
    team_games: z.array(
      z
        .object({
          game_id: game,
          week: z.number().int().min(1).max(18),
          team,
          opponent: team,
          included_plays: count,
          epa_observed_plays: count,
          defense_epa: z.number().nullable(),
        })
        .strict(),
    ),
    unavailable: z
      .object({
        cavaa: z.string().min(1),
        defensive_snaps: z.string().min(1),
        pressure_rate: z.string().min(1),
        coverage_deterrence: z.string().min(1),
        qualification: z.string().min(1),
        player_uncertainty: z.string().min(1),
      })
      .strict(),
    audit: z
      .object({
        chart_issues: z.array(
          z
            .object({
              game_id: game,
              team_id: team,
              role,
              reason: z.string(),
              slot: count.nullable(),
            })
            .strict(),
        ),
        name_issues: z.array(
          z.object({ player_id: playerId, reason: z.string() }).strict(),
        ),
        event_issues: z.array(
          z
            .object({
              game_id: game,
              play_id: count,
              reasons: z.array(z.string()).min(1),
            })
            .strict(),
        ),
        flagged_events: metrics,
        allocated_credits: metrics,
        unallocated_flagged_events: metrics,
        unknown_event_flags: metrics,
      })
      .strict(),
  })
  .strict()
  .superRefine((d, ctx) => {
    const fail = (message: string) => ctx.addIssue({ code: "custom", message });
    const unique = (a: unknown[]) => new Set(a).size === a.length;
    const c = d.coverage;
    if (
      c.players !== d.players.length ||
      !unique(d.players.map((p) => p.player_id))
    )
      fail("Player population mismatch");
    if (
      c.expected_role_cells !== c.completed_games * 2 ||
      d.team_games.length !== c.expected_role_cells
    )
      fail("Team-game coverage mismatch");
    if (
      !unique(d.team_games.map((g) => `${g.game_id}/${g.team}`)) ||
      new Set(d.team_games.map((g) => g.game_id)).size !== c.completed_games
    )
      fail("Duplicate/missing team games");
    if (
      d.team_games.reduce((n, g) => n + g.included_plays, 0) !==
      c.included_plays
    )
      fail("Play totals mismatch");
    if (
      !unique(c.role_cells.map((r) => r.role)) ||
      c.role_cells.some(
        (r) => r.complete_cells + r.blocked_cells > c.expected_role_cells,
      )
    )
      fail("Role coverage mismatch");
    const context = new Map(
      d.team_games.map((g) => [`${g.game_id}/${g.team}`, g]),
    );
    for (const g of d.team_games) {
      const other = context.get(`${g.game_id}/${g.opponent}`);
      if (
        !g.game_id.startsWith(`${d.season}_`) ||
        Number(g.game_id.split("_")[1]) !== g.week ||
        g.week > c.through_week ||
        !other ||
        other.opponent !== g.team ||
        g.team === g.opponent ||
        g.epa_observed_plays > g.included_plays ||
        (g.defense_epa !== null &&
          (g.included_plays === 0 || g.epa_observed_plays !== g.included_plays))
      )
        fail("Invalid team context");
    }
    for (const p of d.players) {
      if (
        !unique(p.games.map((g) => g.game_id)) ||
        !unique(p.teams) ||
        !unique(p.roles)
      )
        fail("Duplicate player evidence");
      const sum = summarize(p);
      if (
        sum.sack_credits !== p.sack_credits ||
        sum.interceptions !== p.interceptions ||
        sum.chart_games !== p.chart_games ||
        sum.event_games !== p.event_games ||
        JSON.stringify(sum.teams) !== JSON.stringify(p.teams) ||
        JSON.stringify(sum.roles) !== JSON.stringify(p.roles)
      )
        fail("Player totals mismatch");
      for (const g of p.games) {
        const t = context.get(`${g.game_id}/${g.team}`);
        if (
          !t ||
          g.week !== t.week ||
          g.opponent !== t.opponent ||
          !unique(g.chart_roles)
        )
          fail("Invalid player game");
      }
    }
    if (
      d.players.reduce((n, p) => n + p.sack_credits, 0) !==
        d.audit.allocated_credits.sacks ||
      d.players.reduce((n, p) => n + p.interceptions, 0) !==
        d.audit.allocated_credits.interceptions
    )
      fail("Event credits mismatch");
    for (const m of ["sacks", "interceptions"] as const) {
      if (
        d.audit.flagged_events[m] - d.audit.allocated_credits[m] !==
        d.audit.unallocated_flagged_events[m]
      )
        fail("Event accounting mismatch");
    }
    if (
      !unique(d.provenance.sources.map((s) => s.kind)) ||
      d.provenance.sources.some(
        (s) =>
          Date.parse(s.fetched_at) > Date.parse(d.cutoff) ||
          Date.parse(s.updated_at) > Date.parse(s.fetched_at),
      )
    )
      fail("Source chronology mismatch");
  });
export type Explorer = z.infer<typeof ExplorerSchema>;
export type Player = z.infer<typeof player>;
export type TeamGame = Explorer["team_games"][number];
export type Filters = { search: string; team: string; role: string };

export function summarize(p: Player, selectedTeam = "ALL"): Player {
  const games = p.games.filter(
    (g) => selectedTeam === "ALL" || g.team === selectedTeam,
  );
  return {
    ...p,
    games,
    teams: [...new Set(games.map((g) => g.team))].sort(),
    roles: [...new Set(games.flatMap((g) => g.chart_roles))].sort(),
    chart_games: games.filter((g) => g.chart_roles.length > 0).length,
    event_games: games.filter((g) => g.sack_credits > 0 || g.interceptions > 0)
      .length,
    sack_credits: games.reduce((n, g) => n + g.sack_credits, 0),
    interceptions: games.reduce((n, g) => n + g.interceptions, 0),
  };
}
const normalized = (s: string) =>
  s
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .trim();
export function selectPlayers(data: Explorer, filters: Filters) {
  return data.players
    .map((p) => summarize(p, filters.team))
    .filter(
      (p) =>
        p.games.length > 0 &&
        (filters.role === "ALL" ||
          (filters.role === "UNMAPPED"
            ? p.roles.length === 0
            : p.roles.includes(filters.role as (typeof ROLES)[number]))) &&
        normalized(`${p.name ?? ""} ${p.player_id}`).includes(
          normalized(filters.search),
        ),
    )
    .sort(
      (a, b) =>
        Number(a.name === null) - Number(b.name === null) ||
        (a.name ?? a.player_id).localeCompare(b.name ?? b.player_id) ||
        a.player_id.localeCompare(b.player_id),
    );
}
export function formatEpa(n: number | null) {
  return n === null ? "Unavailable" : `${n > 0 ? "+" : ""}${n.toFixed(1)}`;
}

export async function loadExplorer(
  base: URL,
  signal?: AbortSignal,
  fetcher: typeof fetch = fetch,
): Promise<{ data: Explorer; snapshotId: string }> {
  const get = async (url: URL) => {
    const r = await fetcher(url, { signal, cache: "no-cache" });
    if (!r.ok)
      throw new Error(
        "The saved snapshot is unavailable. Try again after a verified export is available.",
      );
    const bytes = await r.arrayBuffer();
    if (bytes.byteLength > 5 * 1024 * 1024)
      throw new Error("Snapshot exceeds the supported size.");
    return bytes;
  };
  const directory = new URL("data/", base);
  const decode = (bytes: ArrayBuffer): unknown =>
    JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  const manifest = z
    .object({ schema_version: z.literal(1), snapshot_id: hash })
    .strict()
    .parse(decode(await get(new URL("latest.json", directory))));
  const bytes = await get(new URL(`${manifest.snapshot_id}.json`, directory));
  const digest = [
    ...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
  ]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  if (digest !== manifest.snapshot_id)
    throw new Error(
      "Snapshot integrity check failed. No data has been displayed.",
    );
  return { data: ExplorerSchema.parse(decode(bytes)), snapshotId: digest };
}
