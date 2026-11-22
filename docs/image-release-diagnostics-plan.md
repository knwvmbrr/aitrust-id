# Image release diagnostic capture

Before change: two full website runs failed at catalogue with only output digests;
a detailed direct run passed catalogue and failed mobile-payload fault refusal.
Focused catalogue and all eight mobile fault/recovery controls subsequently
passed. Neither earlier root cause is established. Preserve all observations.

Change only the authored mobile test diagnostic: attach its fixed fault enum to
an exception. Preserve all assertions, timings, supported inputs and production
code. Run the same source-bound website commands with a private bounded output
observer, so a future failure retains its actual command output for diagnosis.
No raw output, private filenames or browsing data is published. The observer
passes identical command/cwd/capture/timeout arguments to subprocess.run.

Risk: diagnostic metadata must not become acceptance or hide a failure. Verify
exit failures still propagate, preserve the original receipts, and require all
64 current commands before protected/public delivery. No reliability repair,
human acceptance or independently validated tag is claimed by a later pass.
