# Selected zlib producer refresh for the MCP branch

The qualified MCP source stays frozen. Its optional per-route policy consumer
changed the whole `tools/dependency_policy.py` identity. The selected zlib
manifest still binds the historical policy helper, so the site correctly refused
at `zlib_source_notice_unavailable` before delivery. The old source archive,
licenses, recipe, five-runtime projection and actual historical WASM observation
remain unchanged. This is a provenance refresh, not permission or runtime proof.

Preserve the complete original manifest under a new digest-named history path.
Invoke the existing `expected_manifest` producer on its exact committed archive,
recipe, recipe license and pinned historical observation. Compare the result
against the original and permit only its actual policy-helper producer hash to
differ. Publish the newly produced canonical manifest only after those checks;
never replace a historical execution record or edit a recorded hash by hand.
Run default verification and deterministic `outputs` in memory, inspect the
six-member source ZIP and compare every emitted source/notice identity. Hash the
five already-installed shared runtime files against the unchanged projection.
Record original/current manifests, producer/input hashes, actual command results
and all three output digests. Recheck all 439 qualified MCP inputs unchanged.

Current free space is 1,299,533,824 bytes, below the retained 2 GiB reserve. This
step may write only small source metadata/history and the immutable execution
record. It must not export source ZIPs to disk, build the site, execute WASM,
install a package, download an archive or alter HOME. Any filesystem export and
`--check-built` are explicitly pending ordinary changed-source hosted execution
with sufficient disk; an in-memory producer result is not relabeled as a local
export or full site pass. The historical WASM version observation is retained,
not claimed as freshly re-executed.

Risks are hidden source drift, source/notice omission and confusing declaration
with execution. Existing producer input hash/size/recipe/path/expansion bounds
stay unchanged; any extra manifest difference refuses before replacement. Full
WASM corresponding source, build reproduction, publisher signature, legal
clearance, MCP admission and full F057/X02 remain false. Distinct review compares
old/current bytes and the actual producer evidence before any push or main merge.
