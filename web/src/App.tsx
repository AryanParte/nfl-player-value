import { useEffect, useMemo, useState } from "react";
import { formatEpa, loadExplorer, ROLES, selectPlayers } from "./data";
import type { Explorer, Player, TeamGame } from "./data";

const PAGE_SIZE = 20;
const number = new Intl.NumberFormat("en-US");
const date = (s: string) =>
  new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "America/New_York",
  }).format(new Date(s));
const roleNames = {
  IDL: "Interior line",
  EDGE: "Edge",
  LB: "Linebacker",
  CB: "Cornerback",
  S: "Safety",
};
const credits = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1));

function Brand() {
  return (
    <a className="brand" href="#top" aria-label="NFL Player Value home">
      <span className="brand-mark" aria-hidden="true">
        PV
      </span>
      <span>
        PLAYER VALUE<span className="brand-sub">NFL · CAVAA RESEARCH</span>
      </span>
    </a>
  );
}
function Frame({ children }: { children: React.ReactNode }) {
  return (
    <>
      <a className="skip" href="#explorer">
        Skip to explorer
      </a>
      <header id="top">
        <div className="header-inner">
          <Brand />
          <nav aria-label="Main navigation">
            <a href="#explorer">Explorer</a>
            <a href="#coverage">Coverage</a>
            <a href="#method">Method</a>
          </nav>
          <span className="build-label">
            <i />
            RESEARCH BUILD
          </span>
        </div>
      </header>
      <main>{children}</main>
      <footer>
        <span>
          NFL PLAYER VALUE <span className="footer-dot">/</span> Independent
          research
        </span>
        <a href="https://github.com/AryanParte/nfl-player-value">
          Source & methodology ↗
        </a>
      </footer>
    </>
  );
}

export function App() {
  const [result, setResult] = useState<{
    data: Explorer;
    snapshotId: string;
  }>();
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setError("");
    loadExplorer(new URL("./", window.location.href), controller.signal)
      .then(setResult)
      .catch((e: unknown) => {
        if (!controller.signal.aborted)
          setError(
            e instanceof Error && e.name !== "ZodError"
              ? e.message
              : "The snapshot failed its quality checks. No data has been displayed.",
          );
      });
    return () => controller.abort();
  }, [attempt]);
  if (!result)
    return (
      <Frame>
        <section className="empty-state" id="explorer">
          <p className="eyebrow">DEFENSE EXPLORER</p>
          <h1>
            {error ? "Snapshot unavailable" : "Loading observed evidence"}
          </h1>
          <p role={error ? "alert" : "status"}>
            {error || "Checking the saved snapshot and its coverage."}
          </p>
          {error && (
            <button
              className="primary"
              onClick={() => setAttempt((n) => n + 1)}
            >
              Try again
            </button>
          )}
          <p className="muted">
            CAVAA estimates are not published in this research view.
          </p>
        </section>
      </Frame>
    );
  return <Dashboard data={result.data} snapshotId={result.snapshotId} />;
}

function Dashboard({
  data,
  snapshotId,
}: {
  data: Explorer;
  snapshotId: string;
}) {
  const [search, setSearch] = useState("");
  const [team, setTeam] = useState("ALL");
  const [role, setRole] = useState("ALL");
  const [page, setPage] = useState(0);
  const [selectedId, setSelectedId] = useState("");
  const [contextTeam, setContextTeam] = useState("");
  const teams = useMemo(
    () => [...new Set(data.team_games.map((g) => g.team))].sort(),
    [data],
  );
  const filtered = useMemo(
    () => selectPlayers(data, { search, team, role }),
    [data, search, team, role],
  );
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, pages - 1);
  const visible = filtered.slice(
    currentPage * PAGE_SIZE,
    (currentPage + 1) * PAGE_SIZE,
  );
  const selected =
    filtered.find((p) => p.player_id === selectedId) ?? visible[0];
  const chartTeam =
    team !== "ALL" ? team : contextTeam || selected?.teams[0] || teams[0];
  const context = data.team_games.filter((g) => g.team === chartTeam);
  const reset = () => {
    setSearch("");
    setTeam("ALL");
    setRole("ALL");
    setPage(0);
    setSelectedId("");
  };
  const blockedCells = data.coverage.role_cells.reduce(
    (n, r) => n + r.blocked_cells,
    0,
  );
  return (
    <Frame>
      {data.data_mode === "synthetic" && (
        <div className="fixture-warning" role="status">
          SYNTHETIC TEST DATA · Not real NFL observations
        </div>
      )}
      <section className="hero" aria-labelledby="page-title">
        <div>
          <div className="eyebrow">
            <span className="live-dot" />
            {data.season} REGULAR SEASON <span className="slash">/</span>{" "}
            THROUGH WEEK {data.coverage.through_week}
          </div>
          <h1 id="page-title">
            Defense Explorer<span className="title-dot">.</span>
          </h1>
          <p className="lede">
            Explore recorded defensive events, first-unit chart roles, and the
            team context behind them.
          </p>
          <div className="asof">
            <span className="tag">ARCHIVED SNAPSHOT</span>
            <span>Cutoff {date(data.cutoff)} Eastern</span>
          </div>
        </div>
        <aside className="admission">
          <div className="field-art" aria-hidden="true">
            <span>10</span>
            <span>20</span>
            <span>30</span>
          </div>
          <p className="eyebrow">INDIVIDUAL CAVAA</p>
          <strong>Not yet estimated</strong>
          <p>
            Defensive attribution has not passed validation. Observed events are
            shown here without an MVP score.
          </p>
          <a href="#method">
            Read the measurement limits <span aria-hidden="true">↘</span>
          </a>
        </aside>
      </section>
      <section className="metrics" aria-label="Snapshot coverage">
        <div>
          <span>COMPLETED GAMES</span>
          <strong>{number.format(data.coverage.completed_games)}</strong>
          <small>Reconciled schedule + play data</small>
        </div>
        <div>
          <span>INCLUDED PLAYS</span>
          <strong>{number.format(data.coverage.included_plays)}</strong>
          <small>Pass/run scope · all teams</small>
        </div>
        <div>
          <span>PLAYERS OBSERVED</span>
          <strong>{number.format(data.coverage.players)}</strong>
          <small>Event records or valid chart roles</small>
        </div>
        <div>
          <span>BLOCKED ROLE CELLS</span>
          <strong className={blockedCells ? "amber" : ""}>
            {blockedCells}
          </strong>
          <small>Team-game roles withheld</small>
        </div>
      </section>
      <section
        className="explorer"
        id="explorer"
        aria-labelledby="explorer-heading"
      >
        <div className="section-heading">
          <div>
            <p className="eyebrow">OBSERVED EVIDENCE</p>
            <h2 id="explorer-heading">The player ledger</h2>
          </div>
          <span className="muted">
            Alphabetical · {number.format(filtered.length)} players
          </span>
        </div>
        <div className="filters">
          <label className="search">
            Find a player
            <input
              type="search"
              value={search}
              placeholder="Search name or player ID"
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(0);
              }}
            />
          </label>
          <label>
            Observed team
            <select
              value={team}
              onChange={(e) => {
                setTeam(e.target.value);
                setPage(0);
              }}
            >
              <option value="ALL">All teams</option>
              {teams.map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </label>
          <label>
            Chart role
            <select
              value={role}
              onChange={(e) => {
                setRole(e.target.value);
                setPage(0);
              }}
            >
              <option value="ALL">All roles</option>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r} · {roleNames[r]}
                </option>
              ))}
              <option value="UNMAPPED">Role unverified</option>
            </select>
          </label>
          <button className="reset" onClick={reset}>
            Reset
          </button>
        </div>
        <p className="filter-note">
          {team === "ALL"
            ? "Counts span all observed teams."
            : `Counts are scoped to ${team}.`}{" "}
          Roles come from valid first-unit charts, not assignments on each play.
          Zero means no valid credit recorded in this scope.
        </p>
        <div className="ledger-layout">
          <div className="ledger-table">
            <div
              className="table-scroll"
              tabIndex={0}
              role="region"
              aria-label="Scrollable player ledger"
            >
              <table>
                <caption className="sr-only">
                  Recorded defensive events and chart membership. This table is
                  not a value ranking.
                </caption>
                <thead>
                  <tr>
                    <th scope="col">PLAYER / CHART ROLE</th>
                    <th scope="col">TEAM</th>
                    <th scope="col" className="numeric">
                      CHART GAMES
                    </th>
                    <th scope="col" className="numeric">
                      SACK CREDITS
                    </th>
                    <th scope="col" className="numeric">
                      INT
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((p) => (
                    <tr
                      key={p.player_id}
                      className={
                        selected?.player_id === p.player_id ? "selected" : ""
                      }
                    >
                      <th scope="row">
                        <button
                          className="player-button"
                          aria-pressed={selected?.player_id === p.player_id}
                          onClick={() => setSelectedId(p.player_id)}
                        >
                          {p.name ?? "Unresolved name"}
                          <span aria-hidden="true">↗</span>
                        </button>
                        <span className="role-line">
                          {p.roles.length
                            ? p.roles.join(" / ")
                            : "Role unverified"}
                          {!p.name && ` · ${p.player_id}`}
                        </span>
                      </th>
                      <td>
                        <span className="team-code">{p.teams.join(" · ")}</span>
                      </td>
                      <td className="numeric">{p.chart_games}</td>
                      <td className="numeric">{credits(p.sack_credits)}</td>
                      <td className="numeric">{p.interceptions}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {filtered.length === 0 && (
              <div className="no-results" role="status">
                <h3>No matching players</h3>
                <p>Try a different name, team, or chart role.</p>
                <button className="primary" onClick={reset}>
                  Clear filters
                </button>
              </div>
            )}
            <div className="pagination">
              <span>
                {filtered.length
                  ? `${currentPage * PAGE_SIZE + 1}–${Math.min((currentPage + 1) * PAGE_SIZE, filtered.length)} of ${filtered.length}`
                  : "0 players"}
              </span>
              <div>
                <button
                  disabled={currentPage === 0}
                  onClick={() => setPage(currentPage - 1)}
                  aria-label="Previous page"
                >
                  ←
                </button>
                <span>
                  {currentPage + 1} / {pages}
                </span>
                <button
                  disabled={currentPage >= pages - 1}
                  onClick={() => setPage(currentPage + 1)}
                  aria-label="Next page"
                >
                  →
                </button>
              </div>
            </div>
          </div>
          <aside
            className="player-panel"
            aria-live="polite"
            aria-label="Player evidence details"
          >
            {selected ? (
              <PlayerDetails player={selected} data={data} />
            ) : (
              <p className="muted">
                Select a matching player to inspect the evidence.
              </p>
            )}
          </aside>
        </div>
      </section>
      <div className="lower-grid">
        <section className="context-section" aria-labelledby="context-title">
          <div className="section-heading">
            <div>
              <p className="eyebrow">TEAM CONTEXT</p>
              <h2 id="context-title">Defensive EPA by game</h2>
            </div>
            <label className="compact">
              Team context
              <select
                value={chartTeam}
                onChange={(e) => {
                  setContextTeam(e.target.value);
                  if (team !== "ALL") {
                    setTeam(e.target.value);
                    setPage(0);
                  }
                }}
              >
                {teams.map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </label>
          </div>
          <p className="muted">
            Observed team outcomes on included plays. Positive favors the
            defense. These points are not assigned to the selected player.
          </p>
          <ContextChart games={context} />
          <div className="chart-foot">
            <span>
              <i className="positive-key" />
              Positive defensive EPA
            </span>
            <span>
              <i className="negative-key" />
              Negative defensive EPA
            </span>
          </div>
        </section>
        <section
          className="coverage-section"
          id="coverage"
          aria-labelledby="coverage-title"
        >
          <p className="eyebrow">POSITIONAL COVERAGE</p>
          <h2 id="coverage-title">What the charts support</h2>
          <p className="muted">
            Valid first-unit role cells out of{" "}
            {data.coverage.expected_role_cells} completed team-games. Membership
            does not establish participation.
          </p>
          <div className="coverage-bars">
            {data.coverage.role_cells.map((r) => (
              <div className="coverage-row" key={r.role}>
                <div>
                  <strong>{r.role}</strong>
                  <span>
                    {r.complete_cells} / {data.coverage.expected_role_cells}
                  </span>
                </div>
                <div className="coverage-track">
                  <span
                    style={{
                      width: `${(r.complete_cells / data.coverage.expected_role_cells) * 100}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
          {blockedCells > 0 && (
            <details>
              <summary>
                {blockedCells} role cells have unresolved evidence
              </summary>
              <ul className="issue-list">
                {data.audit.chart_issues.map((i, n) => (
                  <li key={n}>
                    {i.team_id} · {i.role} · Week{" "}
                    {Number(i.game_id.split("_")[1])}:{" "}
                    {i.reason.replaceAll("_", " ")}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </section>
      </div>
      <section id="method" className="method" aria-labelledby="method-title">
        <div>
          <p className="eyebrow">MEASUREMENT LIMITS</p>
          <h2 id="method-title">Observed is not attributed.</h2>
          <p>{data.scope}</p>
          <p>
            Sack credits and interceptions are event counts. They do not capture
            pressure without sacks, double teams, coverage deterrence, or
            teammates’ contributions. Chart-listed games are not games played.
          </p>
          <p className="muted">
            {data.audit.event_issues.length} event records flagged ·{" "}
            {data.audit.name_issues.length} unresolved player names ·{" "}
            {data.provenance.retrospective_chart_team_games} team-games use
            retrospectively retrieved charts.
          </p>
        </div>
        <dl className="missing-measures">
          <div>
            <dt>CAVAA & player intervals</dt>
            <dd>Unavailable — attribution not validated</dd>
          </div>
          <div>
            <dt>Defensive snaps & pressure rates</dt>
            <dd>Unavailable — verified workload inputs missing</dd>
          </div>
          <div>
            <dt>Coverage & off-ball effects</dt>
            <dd>Unmeasured — assignment data missing</dd>
          </div>
          <div>
            <dt>Leaderboard qualification</dt>
            <dd>Not computed — event counts are not snap exposure</dd>
          </div>
        </dl>
      </section>
      <section className="provenance" aria-labelledby="provenance-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">REPRODUCIBLE BY DESIGN</p>
            <h2 id="provenance-title">The source trail</h2>
          </div>
          <a className="download" href={`./data/${snapshotId}.json`} download>
            Download snapshot ↓
          </a>
        </div>
        <p className="muted">
          This saved view is not a live feed. Newer games and corrections
          require a new verified snapshot. Source retrieval times are shown in
          Eastern time.
        </p>
        <div className="source-grid">
          {data.provenance.sources.map((s) => (
            <div key={s.kind}>
              <a href={s.source_url}>
                <strong>{s.kind.replaceAll("_", " ")}</strong>
              </a>
              <time dateTime={s.fetched_at}>{date(s.fetched_at)}</time>
              <a href={s.license_url}>{s.license_id} ↗</a>
              <p>{s.attribution}</p>
            </div>
          ))}
        </div>
        <p className="snapshot-id">
          Snapshot <code>{snapshotId}</code>
        </p>
      </section>
    </Frame>
  );
}

function PlayerDetails({
  player: p,
  data,
}: {
  player: Player;
  data: Explorer;
}) {
  return (
    <>
      <div className="panel-top">
        <span className="eyebrow">PLAYER EVIDENCE</span>
        <span className="team-code">{p.teams.join(" · ")}</span>
      </div>
      <h3>{p.name ?? "Unresolved name"}</h3>
      <p className="player-identity">
        {p.roles.join(" / ") || "Role unverified"} <span>·</span> {p.player_id}
      </p>
      <div className="detail-counts">
        <div>
          <strong>{credits(p.sack_credits)}</strong>
          <span>Recorded sack credits</span>
        </div>
        <div>
          <strong>{p.interceptions}</strong>
          <span>Recorded interceptions</span>
        </div>
      </div>
      <div className="chart-count">
        <strong>{p.chart_games}</strong>
        <span>games listed in a valid first-unit chart</span>
      </div>
      <p className="muted">
        Event credits appear in {p.event_games} games. This is a lower bound on
        event appearances, not games played.
      </p>
      <div className="withheld">
        <span className="eyebrow">SEASON CAVAA</span>
        <strong>Not estimated</strong>
        <p>{data.unavailable.cavaa}</p>
      </div>
      <details className="player-game-details">
        <summary>Inspect game evidence ({p.games.length})</summary>
        <ul>
          {p.games.map((g) => (
            <li key={g.game_id}>
              <strong>
                Week {g.week} · {g.team} vs {g.opponent}
              </strong>
              <span>
                Chart: {g.chart_roles.join(" / ") || "No valid role record"}
              </span>
              <span>
                {credits(g.sack_credits)} sack credits · {g.interceptions}{" "}
                interceptions
              </span>
            </li>
          ))}
        </ul>
      </details>
    </>
  );
}

function ContextChart({ games }: { games: TeamGame[] }) {
  const extent = Math.max(1, ...games.map((g) => Math.abs(g.defense_epa ?? 0)));
  return (
    <ol className="context-chart" aria-label="Team defensive EPA by week">
      {games.map((g) => {
        const value = g.defense_epa;
        const width = value === null ? 0 : (Math.abs(value) / extent) * 48;
        return (
          <li key={g.game_id}>
            <span className="game-label">
              <b>W{g.week}</b>
              <span>vs {g.opponent}</span>
            </span>
            <div className="context-track" aria-hidden="true">
              <span
                className={
                  value !== null && value < 0 ? "negative" : "positive"
                }
                style={{
                  left: `${value !== null && value < 0 ? 50 - width : 50}%`,
                  width: `${width}%`,
                }}
              />
            </div>
            <strong
              className={value !== null && value < 0 ? "negative-text" : ""}
            >
              {formatEpa(value)}
            </strong>
            <span className="sr-only">
              {g.epa_observed_plays} EPA observations on {g.included_plays}{" "}
              included team plays
            </span>
          </li>
        );
      })}
    </ol>
  );
}
