# Evidence packet: architecture and risks

F-120 needs an inspectable index of the actual execution receipts shipped in a
source download. Add an offline CLI over the existing revalidation contract.
Read the five selected receipt paths from state.json; require bounded public
runs/*.json paths, safely capture the files, and assess each against its exact
current source/command inventory. Include file digests and each refusal reason.
A missing or stale receipt is a failed check, never a silent omission. Capture
state, the revalidation policy and all selected proof/source files before and
after assessment; refuse source drift. Do not execute embedded commands.

A successfully assembled packet is distinct from passing engineering checks.
Neither grants tag release, independent labels, legal clearance or certification.
The packet identifies all open requirement IDs and their existing acceptance
text, preserving human gates. Only explicit owner-authorized acceptance
reallocation may change those records. No endpoint, collection, dependency or
user-input path is introduced. Output contains public paths and digests, not
private host data or assertion text. Test stale, missing, tampered and unsafe
receipt references, changed source, and explicit require-current exit behavior.
