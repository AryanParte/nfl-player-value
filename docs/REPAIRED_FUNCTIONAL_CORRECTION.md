# Saved-proposal restoration correction — November 15

Recorded during the initial known-answer run, before corrected results. The
initial implementation `6259786` restores the defensive proposal component using
the certificate's NFL model plan. `KnownTarget` explicitly overrides that plan's
log-precision mean to **0.0**, whereas the NFL model uses log(400). The saved
adaptive components were correct, but this restored prior component was not the
frozen trial-zero proposal. The first 1,024-trial control failed its coverage/
precision gate. Inspecting the fixture definition identifies this deterministic
implementation defect independently of whether the correction improves results.

Finish and retain the original five-case attempt. Before any NFL functionals,
restore each synthetic proposal using **that target's own plan**. Assert the
complete restored component masses/means/covariances equal the original fitted
proposal, not merely the diagnostic hash (which omits the prior component).
Include full sampling-component hashes in the corrected report and verify them
against the frozen parent geometry and target plan at load time.

Recompute the exact same 5,120 trials under the originally declared seeds, sample
sizes, perturbation, known answers, tolerances and decision rules. This is a
software correction to implement the frozen study, not a new favorable-seed
experiment or fresh statistical validation. Preserve the failed report and
distinguish its evidence from corrected results. If the corrected controls fail,
NFL authorization remains blocked. Do not alter the posterior or sampling rules.

Also capture the executing source fingerprint at run start and check it again
before writing the final report. Source changes during a long-running study must
fail explicitly instead of labeling an old in-memory implementation with hashes
of newer files. This run leaves source files unchanged until the original study
finishes. Documentation/tests do not change its executing statistical code.
