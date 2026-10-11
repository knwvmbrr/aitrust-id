# English redaction development checks

The local service masks the identifiers it detects before PS evaluates the answer. `PII_REDACTED` reports that this procedure ran; it does not mean every sensitive detail was recognized or that the text is safe to share. The phone PS preview does not run this service.

The reproducible diagnostic uses 42 fixed, developer-authored synthetic examples: 38 English cases and four explicitly out-of-coverage challenges. Seven identifier types have annotations: email, phone, name, place, IP address, URL, date/time. Email/web domains, telephone numbers and IP ranges are reserved examples; names are fictional. No real user's answer or personal data was used. These are development checks, not a representative accuracy study, independently labeled holdout or confidence guarantee.

## What the report measures

- **Exact finds:** both the identifier's type and all character boundaries match its annotation. Partial matches count as one missed identifier and an extra candidate.
- **Raw candidates:** overlapping recognizers can produce several candidates for one identifier. Duplicate identical findings are removed before counting. An extra candidate does not necessarily cause extra masking.
- **Actual masking:** the diagnostic observes the spans passed to the existing anonymizer's operation, while forwarding its original call unchanged. Every annotated character must be covered to count as fully masked. Partial and untouched identifiers remain visible in the report.
- **Extra masking:** characters outside annotated identifiers. Unnecessary removal of ordinary words and numbers is a defect even when intended identifiers are masked.
- **Challenges:** non-English context, unusual/obfuscated email forms and invisible-character separation are reported separately. Success on a challenge does not expand the supported language or input contract.

No script executes inspected commands, changes a service, makes an external inference request or collects a user's answer. It starts a separate diagnostic Python process inside the existing staging redactor. It binds the actual redactor/app/model/dependency identities and diagnostic sources before and after. Matching self-reported hashes is not remote attestation, signature trust or accuracy evidence. The diagnostic instruments the pinned engine's private operation interface and refuses incompatible results.

## Run it

Run on the already installed, isolated Linux staging stack with its existing nonroot redactor. The operator needs permission to inspect/exec the staging containers; do not run this against production. No additional dependency, token, account or endpoint is created.

```sh
python3 scripts/measure-redaction-development.py \
  --engine podman --project aitrust-staging \
  --output output/verification/redaction-recognition.json
```

The equivalent existing Docker staging stack can use `--engine docker`; this work does not start local Docker. The Linux engine route is actually exercised separately from Mac unit checks. Output files under `output/` are replaceable local reports; retained `runs/` evidence is exclusive and cannot be overwritten. An unsupported engine identity, stale source, invalid observations or output failure exits nonzero with a fixed message and grants no privacy clearance.

The build uses the specific reviewed staging report and recomputes each count and masked-character result from the fixed annotations and observed spans. Changed source, duplicate/missing cases, corrupted counts or a candidate override refuse the chart. Downloadable observations and fixture files let another operator repeat the checks.

## Observed correction and limits

The original engine recognized only the prefix of the synthetic compressed IPv6 address `2001:db8::27` and left its final two characters unmasked. The narrow correction parses complete, unscoped IPv6 tokens using Python's standard `ipaddress`, preserves upstream IPv4/scoped behavior and scores, and replaces contained truncated IP candidates. It changes no PII score threshold, generation tag, HTTP contract, consent or upload behavior. URL brackets, punctuation, mapped addresses and malformed/scoped/embedded/long tokens have explicit regression checks.

The pre-fix report is retained. Remaining unnecessary masking, raw candidate overlaps and challenge misses are still displayed. No detector is approved by these development examples. Independent recognition acceptance, broader real input/language coverage and human operation remain open in F-023 and T-PII.
