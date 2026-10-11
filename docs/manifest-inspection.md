# Inspect an attached Content Credential

This optional tool reads an explicitly selected PNG and reports the attached
C2PA manifest's validation observations. It keeps signature, asset binding,
signer trust and revocation separate. It does not establish what an image shows,
who created it, or whether an AI contributed. It issues no tag or credential.
The website and text gateway do not depend on this tool.

## Install and try it

Use a separate Python 3.12 or 3.13 environment on Apple silicon macOS or x86-64
Linux. Other platforms and JPEG are not supported by this iteration. From your
downloaded source checkout:

```sh
python3 -m venv "$HOME/aitrust-manifest-env"
"$HOME/aitrust-manifest-env/bin/python" -m pip install --require-hashes -r eval/c2pa-inspection.lock
"$HOME/aitrust-manifest-env/bin/python" scripts/inspect-manifest.py --image tests/fixtures/c2pa-inspection-2026/signed.png
"$HOME/aitrust-manifest-env/bin/python" scripts/inspect-manifest.py --image tests/fixtures/c2pa-inspection-2026/altered.png
"$HOME/aitrust-manifest-env/bin/python" scripts/verify-manifest-inspection.py
```

Replace the fixture path with your own PNG only when you want to inspect it. The
10 MiB input limit, 16-million-pixel structural limit and 12-second child deadline
are fixed. The tool does not execute image content or use filenames as URLs.
It checks the pinned SDK wrapper and native library bytes before importing them.
No global SDK settings are used; each reader gets verification enabled, remote
manifest and OCSP fetching disabled, no allowed network hosts and identity
decoding disabled. It does not add a test root to its trust store.

## Read the result

`OBSERVED` means an attached manifest and its full active validation results were
read. `asset_binding: matched` means the SDK reported that supported asset bytes
match their recorded binding. `claim_signature: matched` is separate. An intact
signature can accompany a changed image; the altered fixture demonstrates that.
`signer_trust: untrusted` describes the configured trust relationship, not fraud.
`revocation: unknown_skipped` means no complete revocation conclusion is issued.
An explicit revocation failure is retained as `reported_revoked`; an isolated
positive OCSP code does not silently clear the unknown state. Ingredient results
stay separate from the active manifest and cannot supply its missing successes.

`NOT_FOUND` means no attached manifest was found in the supported container. It
does not mean human-made, AI-made, safe or true. `UNAVAILABLE` and exit status 2
mean no valid inspection result was obtained: unsupported/corrupt container,
missing or altered SDK, resource limit, native failure or malformed report.
Exit status 0 is inspection success, including NOT_FOUND; it is never a safety
clearance. Missing positive validation is reported as unknown, never pass.

The brief JSON omits author names, GPS, assertion payloads, URLs, thumbnails and
the local path. Its asset hash can still link matching files. Do not automatically
submit it as anonymous research data. All emitted `tags` lists are empty.

## Read the assertions privately

If you explicitly want the complete SDK manifest, including assertion payloads,
create a private directory outside your checkout and request a new report file:

```sh
install -d -m 700 "$HOME/aitrust-private-reports"
"$HOME/aitrust-manifest-env/bin/python" scripts/inspect-manifest.py --image your-image.png --private-report "$HOME/aitrust-private-reports/first.json"
```

The directory must already be owner-held with mode 0700. The new file is 0600;
existing files, links, public directories and paths inside the source checkout
are refused. Full reports can contain identifying or sensitive information.
Nothing is uploaded. A failed export produces UNAVAILABLE and preserves any
existing output. To remove the optional environment, delete the environment you
created; private reports remain yours to keep or remove separately.

## Evidence and limits

Method `attached-c2pa-inspection/1.0.0`, c2pa-python 0.38.0, native SDK 0.91.0.
The optional package is MIT OR Apache-2.0. Package and binary wheel digests are in
`eval/dependencies/c2pa-inspection.json`; the ten-package optional environment is
hash locked separately from the running personal pipeline. SDK and transitive
notices remain part of the broader dependency/licensing audit; this does not
clear F-057 or X-02.

The synthetic frozen fixtures are this project's Apache-2.0 test assets. A white
pixel was signed with an ephemeral test key that was never written. The root is
deliberately untrusted. No real person or authorship is represented. The altered
fixture has a different pixel with correct PNG chunk CRCs, so content binding
failure is distinguishable from a damaged container. Fixture hashes and the
generation source are retained beside them.

The native child supplies fault containment, CPU/output limits, a Linux address
space limit and a clean temporary working directory. It is **not a complete
security sandbox** against a native vulnerability or compromised host. Linux
acceptance executes it in a separately observed network namespace. Mac execution
uses the fixed SDK settings; it supplies no kernel-enforced no-egress claim.
JPEG, remote manifests, full issuer/revocation freshness, watermark readers,
FA/PA interpretation and independent provenance tag release remain separate work.

Primary references: [pinned SDK](https://pypi.org/project/c2pa-python/0.38.0/),
[context settings](https://github.com/contentauth/c2pa-python/blob/main/docs/context-settings.md),
[full validation results](https://opensource.contentauthenticity.org/docs/manifest/reading/manifest-validation/).

## Published parser acceptance

F-025’s declared attached-PNG inspection is complete as of 2026-10-11T15:19:36.016108+00:00. [PR 30](https://github.com/knwvmbrr/aitrust-id/pull/30) merged after 22 required engineering checks and two real optional SDK jobs passed on the reviewed source. The anonymously downloaded merged source also passed all 13 CLI controls. [Hosted execution and protected merge](../runs/2026-10-11-manifest-protected-acceptance.json) · [Merged-source execution](../runs/2026-10-11-manifest-merged-source-acceptance.json).

This completes the parser job, with PNG as its supported format and explicit failures for other inputs. FA/PA tag release, broader media formats and fresh revocation checks stay open in their retained scope jobs. No accuracy or certification gate is waived.
