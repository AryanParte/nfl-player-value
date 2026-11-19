# Integration-aware numerical control results — November 17, 2026

The [frozen design](INTEGRATION_CONTROL_DESIGN.md), committed as 471fe97 before
implementation or new trials, fits a scalar adjustment using independent
integration-replicate means. It preserves the posterior, first-unit and both
sensitivity benchmarks, primary estimates and original numerical tolerances.
**Decision: reject this candidate for numerical certification.** No contribution
module is admitted. All five analytic control gates pass, but only the team
control passes the five-case archived NFL comparison. The team model is not an
individual-player contribution module.

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

The runner recomputes all 144 conditional-solver controls before NFL access.
All five cases complete with 88,065 evaluations each: 86,016 coarse and 2,049 fine.
The first execution takes 3,787.5 seconds across cases; the longest is 922.1
seconds, within the unchanged 90,000-evaluation, 1,800-second per-case and
7,200-second total caps. These local timings are not a portable speed guarantee.
Both complete archived executions match the manifest and all 11 objects byte-for-byte.
The reconstruction takes 3,889.0 seconds across cases; its longest case is 992.2
seconds. Both executions retain the original work/time limits.

| Archived case | Max mean gap + numerical error (posterior SD) | Max endpoint gap + numerical error (CDF) | Gate |
| --- | ---: | ---: | --- |
| Real evolving QB, primary prior | 0.0118956 | 0.00109532 | Fail |
| Real evolving QB, prior shift −ln(4) | 0.0107088 | 0.000976687 | Fail |
| Real evolving QB, prior shift +ln(4) | 0.0132617 | 0.00122358 | Fail |
| Team control | 0.00178568 | 0.000199779 | Pass |
| Continuous-prior stress | 0.0130391 | 0.00291546 | Fail |
| Hierarchy stress | 0.446025 | 0.0190747 | Fail |
| Fixed-year-change stress | 0.0244168 | 0.00156185 | Fail |

Limits remain 0.01 SD and 0.001 CDF. The [full audit](audits/2026-11-17-integration-nfl.json)
retains all priors, benchmarks and functionals. For the QB primary setting, the
worst mean point discrepancy is 0.007682 SD and its numerical allowance is
0.004214 SD. All QB point discrepancies alone pass. This is insufficient precision
to certify agreement, not demonstrated primary-model bias. The hierarchy and
fixed-year-change stress cases also have point discrepancies outside tolerance;
none of their numerical confidence sets excludes the agreement region. Those
large uncertainties must not be presented as proof of agreement either.

The paired plain QB calculation is 0.0120104 SD / 0.00109889 CDF: the adjustment
helps slightly but does not certify. Different seeds from prior studies do not
establish an algorithmic improvement. Across all cases, correction/coarse
influence-standard-error ratios are at most 1.04e-9. More fine work alone cannot
address the observed coarse error. No primary model or prediction object changed.

## Failure analysis and next decision

The fitted objective minimizes each unnormalized integral's variance. A ratio
N/Z instead depends locally on N−rZ, including numerator/mass covariance.
Post-result diagnostics use the fixed primary anchors r=0, 0.025 and 0.975; these
are not asserted to be true NFL ratios. The diagnostic neither refits controls
nor changes estimates, intervals or gates.

At the QB primary setting, training upper-CDF numerator variance improves for
all 171 contrasts, but variance of N−0.975Z worsens for 164/171 (median ratio
1.0643). On evaluation draws, all 171 worsen (median 1.0730), even though every
upper-CDF numerator again improves. Thus loss of cancellation is visible within
training and cannot be explained solely by fitting noise. The analytical
regression fixture isolates this effect with independent zero-covariance vectors:
removing denominator noise while leaving the numerator unchanged increases the
ratio-influence variance by exactly 1+5r². Zero baseline variance remains undefined,
never a zero improvement. Training/evaluation phases and prior order stay separate.

Mean contrasts still block certification. Their evaluation variance improves only
modestly (median fixed-anchor ratio 0.9653), with 15/171 worse. Fixing CDF cancellation
alone cannot be assumed to fix the mean gate. The hierarchy stress case has a
maximum replicate mass share of 10.3866%, compared with at most about 1.5871% in
these known targets. Its paired plain result is also poor (0.451387 SD / 0.0192083
CDF). This is a separate tail/concentration limitation, not solely a bad control
fit; the current analytic coverage result does not certify that harder regime.
These are correlated diagnostics, not independent counts of successful evidence.

Next freeze one bounded joint mass/numerator control candidate targeting normalized
functional variance, using the existing zero-mean basis and at most the two
composite directions for mass and numerator. Add analytically solvable tail-stress
controls before evaluating new draws; retain all existing cases and gates. This
proposal is not implemented or validated. It must improve the mean and endpoint
requirements, not merely CDF cancellation. If the broader numerical check still
fails, record that stop before launching the unfinished 192-fit player calibration.
No favorable-seed retry, prior change, wider player interval or selected plain
fallback is authorized by these results.

The saved football cohort remains 57 QBs / 122 completed games / 8,996 2026
dropbacks through November 7 evening, with 37 first-unit members, 57 sensitivity
members and 38 negative first-unit estimates. Week 10 stays sealed. Participation,
defensive comparability, observational admission and a scored leaderboard remain
unfinished; this numerical study is intermediate work toward the original product.

## Verification and review

Final local make check passes 487 Python tests and 27 frontend contracts,
Ruff/format, TypeScript/build, compilation and whitespace. Diagnostic source
53a4c71 passes [hosted CI](https://github.com/AryanParte/nfl-player-value/actions/runs/44238231094)
on Python 3.11–3.13 and the dashboard, including 12 Chromium scenarios. Final
reporting-head CI is checked separately. These software checks do not establish
statistical admission. Review the signed covariance fit, independent entropy,
unchanged work/caps, complete failure denominators and post-result diagnostic
scope. No numerical package source changed after producer 8a990d5.

The [execution audit](audits/2026-11-17-integration-executions.json) binds producer
revisions, environment, log hashes, both runs' timings, exact reconstruction and
source/deployment observations. The run started November 17 and finished November
18 local time. No new dependency, service cost, purchase, deployment, other-project
edit or development-automation change. Research stores remain local.

## Reproduction

Control producer: `8a990d5290b90b8ee9143ce73b74f7478a223522`.
Control report: `983b683508242a3d0dd5c10f47329208f6b681c8fb0b55eccbc1eb4928b181fd`.
Archived producer: `62cd9394e476fb413a577d413de862d3579ef921`.
Archived report: `a7a101c9163d0be23c2c96aec8501c8b97ae8fd4e9d3aa18e2c218285b32531f`.
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
OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
  -m nfl_value.coarse_control_cli --controls-store data/derived/integration-controls-blocks \
  --output-store data/derived/integration-nfl --offline archive \
  983b683508242a3d0dd5c10f47329208f6b681c8fb0b55eccbc1eb4928b181fd
```

A new execution at a different documentation commit records that commit and may
change the manifest ID. Use the CLI's `replay REPORT_ID` with a restored store for
exact recorded-revision reconstruction. Immutable local study stores are not
durable remote research retention.
