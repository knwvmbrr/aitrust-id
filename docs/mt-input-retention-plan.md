# MT full-input retention repair — architecture before edit

Base: `3941603265c763de07d9f7d91e465e0832db39d1`. Owner: `/root/web_camo`.
Existing scope: T-MT, F-019a/b/c, F-142. This is an existing input-integrity defect,
not a new tag, method, scope task or claim of full original completion.

The MT editor declares HTML `maxLength=16000`, measured in UTF16 code units,
while the existing client accepts at most8000 Unicode codepoints/32000UTF8 bytes.
Native insertion of8001 emoji can therefore clip to8000 and become accepted input.
A user may see a successful observation for text they did not choose to shorten.
First reproduce that actual browser path on the frozen existing built site;
retain exact source/artifact identity and count-only evidence, never private text.

The only product change removes HTML clipping and makes the existing unchanged
validation limit explicit. Preserve all supplied text in application state; on
oversize refuse before a worker, keep the complete text, set the existing input
invalid state and move focus to its associated error. No canonical method,
client, worker, normalization, payload, source identity or production mapping changes.

Add a reusable production MT-modal input verifier plus a bounded owned runner.
After the delta, a normal own-checkout build and actual Chromium/WebKit checks
must cover intact oversize emoji and ASCII under all three existing selections,
zero new worker on refusal, three complete canonical records (urgency, authority,
curly-quotation), the exact accepted boundary, private details, edit/Clear/modal
unmount cleanup, no input requests/storage/console and existing PS/HP recovery
after an optional MT failure. Preserve the before proof separately. No broad
whole-website suite or repeated unchanged canonical cohort is needed for this UI edit.

Risks: retaining a large paste consumes browser/UI memory; no hard renderer heap
or forensic-erasure guarantee is added. Native input insertion and codepoint vs
UTF16/byte boundaries must be measured rather than inferred from static markup.
A browser engine is not a physical phone or human screen reader. Parent owns
shared hooks, scope/state, exact-source inventories and protected/public delivery.
