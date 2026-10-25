# Defense Explorer dashboard

React/TypeScript renders an offline Python export. It does not calculate player
value. The initial page is an observed defensive ledger, not an MVP leaderboard.
See [the data contract](../docs/DEFENSE_EXPLORER.md) for scope and limitations.

Use **Node 24** and the committed npm lockfile. From the repository root:

```sh
npm --prefix web ci --ignore-scripts --no-fund
npm --prefix web run check
```

`check` validates formatting, runs the Vitest contracts, checks TypeScript and
builds `web/dist`. No live NFL source is used in CI. Build/replay/export a real
snapshot with the Python commands in the data contract, then run:

```sh
npm --prefix web run build
npm --prefix web run preview
```

The preview binds only `127.0.0.1:4317` and refuses to reuse an occupied port.
`npm --prefix web run dev` uses the same reserved local port. No telemetry,
external fonts, paid service, application server or database is required. The
relative asset base supports a static subdirectory deployment. HTTPS (or local
localhost) is required for the browser's SHA-256 integrity check.

The build deliberately contains no fake fallback snapshot. Without an export,
the page explains that its snapshot is unavailable. Actual exports under
`web/public/data` and `web/dist` are ignored by Git. Hosting, durable snapshot
retention and independent weekly production refresh are separate release tasks;
this unit does not deploy them.

## Browser verification

Run from the repository root after building. The browser cache is local to this
project; do not share ports, cache directories or processes with the other NFL
project.

```sh
cd web
PLAYWRIGHT_BROWSERS_PATH=../work/playwright-browsers npx playwright install chromium
PLAYWRIGHT_BROWSERS_PATH=../work/playwright-browsers npm run test:e2e
```

Playwright starts its own production preview on `127.0.0.1:4318`, uses synthetic
JSON routes, and shuts down that server afterward. Tests exercise filters,
details, keyboard/mobile behavior, negative/missing team EPA, integrity failures,
unadmitted scores, and retry. They are interface evidence, not football model
validation. CI installs Chromium with its Linux system dependencies.

`tests/fixture.json` is explicitly synthetic and checked against the Python
producer in the offline Python suite. Update both contracts deliberately when
changing the snapshot schema. Do not weaken validation to accept a broken export.
Use `npm --prefix web run format` before a commit and review the diff afterward.
