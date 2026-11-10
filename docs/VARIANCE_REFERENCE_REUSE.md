# Exact reference work reuse — November 10, before cached NFL results

The first uncached real QB and team references exhaust 90,000 target evaluations.
The corresponding QMC checks pass. This does not establish reference accuracy or
reject the statistical model. Preserve those runs and finish their other three
declared cases. Their original artifact must remain separate from any follow-up.

Inspection of pinned SciPy 1.15.3 finds repeated **identical** rule nodes: its
estimate evaluates the high-order rule, then its error evaluates both the high
and embedded lower rule again. All lower nodes are in the higher rule. In four
dimensions this is 155 requested solves for 57 distinct nodes per region; in three
dimensions it is 91 for 33. Each subdivision also splits all dimensions, creating
16 or 8 child regions. This is a measured source of work, not proof that removing
it will make the independent reference converge.

The frozen pilot explicitly permits exact node reuse after numerical-equivalence
checks. Implement a bounded 1,024-entry cache inside each reference call, keyed by
the complete log-precision vector and its exact proposal log density. Cache only
the deterministic integrand vector; never share entries between targets, cases,
contrasts, summaries or sensitivity settings. No rounding, interpolation, truncation,
early convergence or changed posterior is allowed. Report requested evaluations,
hits, misses and retained entries. The existing target counter charges actual
conditional solves; repeated lookups cost no solve. The cache is bounded to about
12 MiB of numeric payload for the 171-contrast/three-sensitivity real QB case.

Before running cached NFL results, require exact equality with the uncached
analytic reference, including estimates, errors, subdivision count and pass/fail
decision; assert the conditional solve count falls and the capacity is enforced.
The independent small-model/known-answer assertions remain unchanged.

`variance-reference-cached-v1.json` adds only `reference_cache_nodes: 1024` to the
smooth-reference plan. Run the same five cases, original prior, intervals, gates,
90,000-solve/900-second case limits and 3,600-second total limit. This is exact
work reuse under the original plan, not another numerical integration method or
statistical alternative. Do not increase budgets or tolerance thresholds. Retain
every failure and unattempted case. Independently rebuild cached results offline;
report any incomplete or nonidentical verification. No new calibration or Week 10
outcomes are opened, and no pilot alone admits CAVAA.
