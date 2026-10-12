# Bind a blind review to its execution recipe

Architecture before implementation. Codex; F-050, F-108 and F-120. The current
packet pins the evaluator file, gates and instructions, but normalization and
installed execution dependencies can change without invalidating that file hash.
Fix the private review workflow, without changing assertion versions, tag methods,
public endpoints, collection permissions or reviewer phone-form fields.

New private packets use manifest v2 and a separately hashed execution-context
member. It records selected evaluator, frozen normalization data, evaluator lock,
review preparation and evaluation route source hashes, Python implementation and
executable, relevant standard-library code and actual installed FastAPI/Pydantic/
Starlette code identities. Compare validates the frozen member and the current
recipe before interpreting labels; any drift is unavailable. New files retain
owner-private I/O bounds. No detector or network is invoked during freeze/compare.

Legacy v1 packets remain readable for label comparison, explicitly without a
complete execution binding. A require-binding option refuses them. Never silently
upgrade historical evidence, erase labels or claim an old packet froze dependencies
it never captured. Phone forms retain their existing v1 structure and opaque hashes.

Risks: hashes are consistency checks, not trustworthy timestamps or reviewer
attestations; an owner controlling both files can rewrite them. Dependency hashes
describe the selected host, not every possible service/browser route. Runtime
updates require a new packet and can inconvenience a coordinator; explain this
before freeze. Dependency enumeration must be bounded, reject unsafe file names
and fail on missing/unstable files. Receipts contain no private paths or example
text. Test changed normalization, helper, interpreter/dependency identities,
missing/tampered members, legacy labels-only handling, private file attacks,
actual CLI round trips and source stability. Retain disagreement and ambiguous
items; independent humans, sampling and calibration stay separate open gates.

Before publication, bind the existing opaque reviewer-form method digest to the
complete selected execution recipe for manifest v2. Legacy v1 keeps its original
evaluator-file digest. This prevents forms silently crossing dependency contexts
without changing phone-form fields. Missing installed dependencies must produce
fixed unavailable diagnostics; they must not print exception values or paths.
