# Complete active regression coverage — 2026-10-08

CI already runs three active fixture files through pytest, plus separate literal
live-gap cases. Its statistical gate runs only ps_v1. The fourth active file,
live_gap_v1, is not consumed as a file. Counterexamples_v1 retains superseded
labels and must not become a current acceptance dataset.

Add an explicit hashed manifest classifying every JSONL as active or historical.
Use one runner for active datasets, with a nonzero exit for classification errors,
missing/unregistered files or changed bytes. Run this runner as a separate CI job.
Keep the statistical release gate unchanged: regression success is not independent
accuracy or release approval. Extend existing fixture pytest coverage through the
manifest and prove failures with a changed file, an unregistered file and a real
misclassification fixture. No evaluator or gateway behavior changes are needed.
