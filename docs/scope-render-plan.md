# Keep scope projections together

Architecture before change, November 6: scope-progress.py --render updates the
completion ledger Markdown but leaves the task index stale. CI correctly rejected
the F-158 20-to-60 change because two views disagreed. The runtime agent checks
passed; the failure was an incomplete documentation pipeline.

Keep the existing JSON authority and both existing renderers. After validating
the ledger and rendering its Markdown, the canonical --render command executes
the existing render-scope-plan.py generator in-process. It regenerates the task
index and associated plan/master projections from their original inputs. A
generator failure must propagate as a nonzero command; no success JSON is printed.
Keep the canonical command's single JSON result on stdout; generator progress goes
to stderr so existing machine consumers do not receive mixed output.
Do not alter IDs, percentages, acceptance or the pure ledger renderer's interface.

Exercise a throwaway copy using real referenced public evidence. Deliberately
corrupt the task index, invoke the canonical command and verify all 202 percentages.
Also force the secondary renderer to fail and require a nonzero command without a
pass claim. Existing scope/index checks remain required. No runtime or tag
acceptance is granted by regenerating these views.

## Historical evidence during a multi-commit delivery

The branch build found that an earlier committed change event correctly hashes its then-current scope snapshot, but later progress changes that snapshot. Keep committed events immutable. For an event introduced earlier in the reviewed Git history, verify its evidence against the exact introducing commit when current bytes differ. Uncommitted events still require current evidence. Current changed files still require a fresh matching event; a historical snapshot cannot cover a new change. Refuse edited/re-added events and absent or mismatched historical evidence. Verify real multi-commit histories and refusal paths.
