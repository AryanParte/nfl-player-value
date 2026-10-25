import { describe, expect, it } from "vitest";
import fixture from "../tests/fixture.json";
import { ExplorerSchema, formatEpa, loadExplorer, selectPlayers } from "./data";

const data = () => ExplorerSchema.parse(structuredClone(fixture));
describe("versioned observed evidence", () => {
  it("accepts the Python-produced synthetic contract with unavailable values", () => {
    expect(data().players).toHaveLength(4);
    expect(
      data().players.every(
        (p) => p.cavaa === null && p.defensive_snaps === null,
      ),
    ).toBe(true);
  });
  it.each([
    (d: any) => {
      d.ranking_ready = true;
    },
    (d: any) => {
      d.players[0].cavaa = 20;
    },
    (d: any) => {
      d.players[0].defensive_snaps = 0;
    },
    (d: any) => {
      d.players[0].sack_credits = 2;
    },
    (d: any) => {
      d.players.push(d.players[0]);
    },
    (d: any) => {
      d.provenance.sources[0].fetched_at = "2027-01-01T00:00:00Z";
    },
    (d: any) => {
      d.team_games[0].epa_observed_plays = 0;
    },
  ])(
    "rejects invented values, inconsistent evidence and future sources",
    (mutate) => {
      const d = structuredClone(fixture);
      mutate(d);
      expect(ExplorerSchema.safeParse(d).success).toBe(false);
    },
  );
  it("filters chart roles without inventing a role for event-only players", () => {
    expect(
      selectPlayers(data(), { search: "", team: "ALL", role: "EDGE" }).map(
        (p) => p.player_id,
      ),
    ).toEqual(["00-0000001"]);
    expect(
      selectPlayers(data(), { search: "", team: "ALL", role: "UNMAPPED" }),
    ).toHaveLength(2);
  });
  it("recomputes team-scoped totals instead of showing another team’s credits", () => {
    const d = data();
    d.players[0].games.push({
      ...d.players[0].games[0],
      team: "NYJ",
      opponent: "BUF",
      game_id: "2026_02_BUF_NYJ",
      week: 2,
      sack_credits: 3,
    });
    const p = selectPlayers(d, {
      search: "PLAYER 1",
      team: "NYJ",
      role: "ALL",
    })[0];
    expect(p.sack_credits).toBe(3);
    expect(p.chart_games).toBe(1);
    expect(p.teams).toEqual(["NYJ"]);
    expect(
      selectPlayers(d, { search: "unknown", team: "ALL", role: "ALL" }),
    ).toEqual([]);
  });
  it("preserves negative context and never formats missing as zero", () => {
    expect(formatEpa(-2.3)).toBe("-2.3");
    expect(formatEpa(null)).toBe("Unavailable");
    expect(formatEpa(0)).toBe("0.0");
  });
  it("verifies exact bytes and loads only hash-addressed same-origin assets", async () => {
    const bytes = new TextEncoder().encode(JSON.stringify(fixture));
    const digest = [
      ...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
    ]
      .map((x) => x.toString(16).padStart(2, "0"))
      .join("");
    const urls: string[] = [];
    const fake: typeof fetch = async (input) => {
      urls.push(String(input));
      return new Response(
        urls.length === 1
          ? JSON.stringify({ schema_version: 1, snapshot_id: digest })
          : bytes,
      );
    };
    expect(
      (await loadExplorer(new URL("https://example.com/nfl/"), undefined, fake))
        .data.players,
    ).toHaveLength(4);
    expect(urls).toEqual([
      "https://example.com/nfl/data/latest.json",
      `https://example.com/nfl/data/${digest}.json`,
    ]);
    let calls = 0;
    const bad: typeof fetch = async () =>
      new Response(
        ++calls === 1
          ? JSON.stringify({ schema_version: 1, snapshot_id: "0".repeat(64) })
          : bytes,
      );
    await expect(
      loadExplorer(new URL("https://example.com/"), undefined, bad),
    ).rejects.toThrow("integrity");
  });
  it("rejects missing pointers and path injection without requesting an external snapshot", async () => {
    await expect(
      loadExplorer(
        new URL("https://example.com/"),
        undefined,
        async () => new Response("", { status: 404 }),
      ),
    ).rejects.toThrow("unavailable");
    let calls = 0;
    await expect(
      loadExplorer(new URL("https://example.com/"), undefined, async () => {
        calls++;
        return new Response(
          JSON.stringify({
            schema_version: 1,
            snapshot_id: "https://evil.example/data",
          }),
        );
      }),
    ).rejects.toThrow();
    expect(calls).toBe(1);
  });
});
