# Measure the complete local-service check

This development tool sends fixed synthetic text to an **already-running dedicated staging stack**, using the existing loopback gateway. It does not start Docker, change production, collect user content or accept a speed budget.

Use the same checked source as your staging services, with the existing hash-locked gateway/evaluation dependencies installed. Run as the ordinary account holding a private `0600` staging credential file in a `0700` directory. Do not place the token in the command or paste it into chat.

```sh
python3 scripts/measure-pipeline-performance.py \
  --project aitrust-staging \
  --env-file /your/private/staging.env \
  --output output/verification/pipeline-timing.json
```

Only `127.0.0.1:8787/healthz` and `/v1/evaluate` are used; proxies and redirects are refused. Confirm that the existing service at that port is your staging stack. This command does not provision a stack or discover remote hosts. It validates each returned assertion, the full source-matched runtime pipeline identity, expected synthetic outcomes and privacy headers before accepting timing. The sample includes ordinary text, a remote-command pattern and an email-plus-command pattern at 256, 2,000, 8,000 and 20,000 characters. Configured URL redaction may accompany the command finding. No sample command is executed or fetched.

There are 20 repeated requests per profile, plus one first observed request. The first observed request is **not** a measured service cold start. The round trip includes loopback HTTP, English redaction and tagging. The wire field `evaluator.latency_ms` is measured by the gateway around the pipeline; it is **not detector-only time**. Both fields retain the observations and exact nearest-rank median, 95th percentile and maximum. These are finite development samples, not population guarantees or accuracy measurements. Phone startup, internet latency and real-device usability remain separate.

The public four-row display takes the maximum warm round-trip 95th percentile across the three profiles at each input size. It appears only for the two tags in that measured service path. It is build-time data: no automatic check or upload is added to a modal. The build rejects changed sources, missing samples, duplicate profiles and fabricated quantiles. Downloaded JSON shows all conditions and durations without text or credentials.

The first benchmark wrongly required the command sample to have no procedural redaction tag. The actual configured redactor also found the synthetic URL. That failed prototype run is preserved in `runs/2026-10-11-pipeline-benchmark-expectation-failure.json`; the corrected benchmark admits that configured procedure and keeps the requested command finding required. The prototype source is retained privately and its hash is historical, not current acceptance.

The corrected actual staging run contains 253 requests across 12 profiles. Separate execution evidence checked all three running container app sources against the source under test. This proves that bounded staging execution, not universal security, recognizer accuracy or a production latency SLA. F-113 remains open until physical-phone/full-route acceptance and an agreed route-specific budget.

For operational diagnosis, retain failed-command raw output only in an owner-controlled, non-symlink `0700` directory outside the source checkout, using exclusive new `0600` files and a bounded log size. Public execution receipts keep output hashes and fixed failure states. Do not publish raw operational logs or credentials. The first hash-only website receipt lost its diagnostic text; a separate run reproduced the stale disclosure-count assertion and a fresh run checks its correction.

Review found that the first benchmark checked the evaluator but did not itself bind the running gateway and redactor to the recorded checkout hashes. The separate container witness did not enforce display admission. That run remains historical. The corrected client requires a valid, matching full pipeline identity on every response, checks gateway/normalization and all five redactor sources, checks the model identity entries, and refuses identity drift during the run. The build separately checks the reported identity shape, its canonical digests and source bindings. This is consistency with self-reported service identity, not cryptographic remote attestation or protection against a compromised service lying about its code.
