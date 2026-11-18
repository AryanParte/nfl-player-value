# Integration-aware numerical control results — November 17, 2026

The [frozen design](INTEGRATION_CONTROL_DESIGN.md), committed as 471fe97 before
implementation or new trials, fits a scalar adjustment using independent
integration-replicate means. It preserves the posterior, first-unit and both
sensitivity benchmarks, primary estimates and original numerical tolerances.
No contribution module is admitted by this study.

## Known answers and reconstruction

All five gates pass on 5,120 complete trials under source 8a990d5. Two complete
network-disabled executions match the manifest and all 11 objects, including all
raw fitting/evaluation records. They are reconstructions of the same draws, not
10,240 independent trials. The [audit](audits/2026-11-17-integration-controls.json)
retains each functional, failed-gate denominator and paired diagnostic.

| Analytic target | Joint numerical coverage | Trials meeting precision | Gate |
| --- | ---: | ---: | --- |
| 0 | 95.1172% | 100% | Pass |
| 1 | 95.7031% | 100% | Pass |
| 2 | 95.6055% | 100% | Pass |
| 3 | 96.4844% | 98.0469% | Pass |
| 4 | 94.9219% | 99.8047% | Pass |

Every deliberately incorrect endpoint is rejected. These finite controls pass the
unchanged joint/marginal coverage and precision rules; they do not establish
universal 95% coverage. The lowest marginal coverage is 93.6523%, with one-sided
undercoverage p=0.03166, above the preregistered family-adjusted 0.01/35 threshold.
The joint one-sided 95% lower bounds range from 93.6445% to 95.3836%.

Adjusted/plain empirical variance ratios range from 0.258 to 1.211 across the
35 correlated target-functionals. Improvement is not uniform, even though fitting
minimizes training replicate variance. The plain calculation is a paired
diagnostic, never a selectable fallback. Numerical coverage is separate from
player calibration and observational attribution.

## Recovered execution failure

Both initial executions at cc83843 stopped after target 2's trials because the
embedded checkpoint exceeded the unchanged 128 MiB object cap. They retain only
the first two target records; targets 3 and 4 were unattempted and no complete
certificate was issued. The [failure audit](audits/2026-11-17-integration-storage-failure.json)
preserves logs, original IDs, and the subsequent byte-identical recomputation of
both retained cases.

Reconstructing the old wrapper around the corrected target-2 record produces
138,176,740 bytes: nesting adds indentation to a 129,521,656-byte case. A 216-byte
reference checkpoint avoids that overhead. All five actual case objects fit the
cap individually. A bounded trial-block fallback is separately exercised by
regression fixtures, including missing, reordered, changed and corrupted blocks;
it was not needed for these actual case objects. No numerical function or fitting
module changed in the storage repair. Because the whole-package source fingerprint
did change, all five targets were recomputed twice rather than reusing a partial
certificate.

## Archived NFL comparison

The complete known-answer gate authorizes the next frozen comparison, including
recomputation of 144 conditional-solver controls before NFL access. Both archived
executions will run sequentially with the original 90,000-evaluation, 1,800-second
per-case and 7,200-second total caps. The current known-answer result does not
certify archived NFL precision. Results and the bounded decision follow here once
those executions finish; no player calibration or admission is claimed meanwhile.

## Reproduction

Control producer: `8a990d5290b90b8ee9143ce73b74f7478a223522`.
Control report: `983b683508242a3d0dd5c10f47329208f6b681c8fb0b55eccbc1eb4928b181fd`.
The package source guard requires the recorded numerical source; later documentation
commits do not change it. Use the pinned environment and archived dependencies.

```sh
OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
  -m nfl_value.coarse_control_cli --plan config/coarse-control-v2.json \
  --output-store data/derived/integration-controls-blocks --offline known
PYTHONPATH=src .venv/bin/python scripts/analyze_coarse_controls.py \
  data/derived/integration-controls-blocks \
  983b683508242a3d0dd5c10f47329208f6b681c8fb0b55eccbc1eb4928b181fd \
  --reconstruction data/derived/integration-controls-blocks-offline
```

A new execution at a different documentation commit records that commit and may
change the manifest ID. Use the CLI's `replay REPORT_ID` with a restored store for
exact recorded-revision reconstruction. Immutable local study stores are not
durable remote research retention.
