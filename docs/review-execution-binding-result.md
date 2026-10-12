# Blind-review execution binding — development result

Codex implemented an owner-private manifest-v2 execution recipe for new PS review
packets. The unchanged phone/CSV review formats still support blind labeling.
Comparison checks frozen normalization, preparation/evaluation sources, selected
Python runtime/standard-library code and ten declared installed import dependencies
before reading labels and again after comparison. It does not run the detector.

84 focused tests and 21 actual CLI controls passed on both macOS and Linux. The
Linux run denied IPv4, IPv6 and Unix sockets to the worker and its children. Source
hashes matched; only the owned staging directory was removed. See the source-bound
`runs/2026-10-12-review-execution-focused.json`, `review-execution-cli.json`,
`review-execution-linux.json` and `review-execution-linux-cleanup.json` records.

Controls cover changed normalization code/data, evaluation/preparation helpers,
Python/stdlib/dependency version and code drift, missing or altered recipes,
duplicate fields, symlinks, shared permissions, oversized files, mid-operation
drift and legacy label preservation. New packets remain private and create no
network request, account, collection enrollment or production configuration.

Legacy manifest-v1 packets remain readable for labels only and explicitly lack
the execution binding. `--require-execution-binding` refuses them. No assertion
protocol migration is adopted, no historical packet is rewritten and no existing
label is discarded. Host updates may require a new packet; retain the originals.

These hashes are consistency checks for a selected offline route. They do not
attest a hostile host, trustworthy chronology, independent people or sample
representativeness. F-050, F-108 and F-120 remain open for their full acceptance;
independent labels, agreed sampling, adjudication, calibration and outside
implementation acceptance cannot be supplied by synthetic engineering controls.
