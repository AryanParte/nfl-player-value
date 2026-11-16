# Bounded storage recovery, declared after the completed numerical study

Both version-2 numerical executions at `3774295` complete all five controls and
pass every declared gate. Each preserves five byte-identical case checkpoints.
Both then fail to save the aggregate study because it exceeds SnapshotStore's
128 MiB per-object limit. The checkpoints total about 221 MiB. This is an I/O
failure, not a failed numerical trial; no NFL comparison is authorized yet.

Preserve that limit. Store large studies as a small index plus separately hashed
case objects; bind the exact reconstructed logical study with a SHA-256 hash.
Validate order, uniqueness, missing/corrupt objects and the logical hash before
the existing numerical validation. Small existing studies retain their format.
Do not alter production publication/retention bounds or any statistical rule.

Recover this completed study from all five declared checkpoints, never a subset.
Require the original producing revision on each checkpoint and verify its full
raw content hash. Before recovery, prove that every statistical package module
is byte-identical to `3774295`, except the storage-only `save` and `load` functions
in `repaired_functional.py`; for that module require identical parsed syntax
trees after removing exactly those two functions. No other computational change
may be included in this recovery. Recompute every existing known-answer decision
from the retained raw levels.

Record a separate immutable recovery receipt linking the original checkpoint
hashes and producing source fingerprint to the new packaging revision, report
and logical study hash. The report's code revision identifies packaging/validation;
the receipt explicitly identifies the original numerical execution. Independently
recover both complete executions and compare the manifests and all object bytes.
This is staged reconstruction of the same declared draws, not new statistical
trials or a claim that the updated one-shot CLI has already rerun the long study.

Only a complete verified recovered certificate may authorize the existing five
archived comparisons. Their frozen randomizations, limits and stopping rules stay
unchanged. No model, source cohort, prior, player interval or admission changes.
