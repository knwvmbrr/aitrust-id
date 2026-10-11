# Reference the project clearly

AI Trust ID is the project name. Its specification, source and development tools
are public. There is no operating certification-mark licensing or accreditation
programme. These guidelines do not claim trademark registration, clearance,
exclusive ownership of the words, or rights over another party's mark.

## What to say today

Descriptive attribution such as **“Built from the AI Trust ID reference source,
revision [the actual commit]”** identifies the origin of your implementation.
Show your own publisher and product name prominently. If modified, say so and
identify the revision and changes. Keep the required copyright, license and
notice files. Do not imply the project publisher reviewed or endorsed your build.
A code license is not general permission to use a project's branding as your
own product brand. [Apache-2.0 section 6](https://www.apache.org/licenses/LICENSE-2.0.html)
separately limits trademark permissions to customary origin/notice references.

Do not use **“AI Trust ID certified,” “approved,” “accredited,”** a certification
seal, or a ® symbol on the basis of a passing test, source signature or download.
No present tool grants those permissions. Refer to exact checks, exact versions
and their limits instead: **“Our build passed the listed engineering checks.”**
A signed record proves integrity under a selected key; it does not prove content
truth, a person's identity, human authorship or tag accuracy.

## Make an inspectable self-declaration

Use Node 24. Save an input JSON in a private working directory alongside the
actual evidence files. This is the template; replace the example revision,
publisher, implementation, limitation and file name with your actual values:

```json
{
  "version": "implementation-self-declaration/1.0.0",
  "publisher": "Your publisher",
  "implementation": "Your implementation and version",
  "source_revision": "0123456789abcdef0123456789abcdef01234567",
  "profile": "engineering-self-declaration",
  "limitations": ["No independent tag-accuracy or human-accessibility validation"],
  "checks": [
    {"name": "Actual engineering check", "result": "pass", "evidence": "engineering-run.json"},
    {"name": "Physical phone review", "result": "not_tested", "evidence": null}
  ]
}
```

Run from the downloaded repository:

```sh
node scripts/conformance-statement.cjs create /your/private/input.json /your/private/statement.json
node scripts/conformance-statement.cjs check /your/private/input.json /your/private/statement.json
```

Use real paths. Nothing is uploaded. The destination must be new. Evidence paths
are relative to the input file; regular files only, no symlinks or parent-path
traversal. Each evidence file is limited to 256 KiB. The output includes publisher,
source revision, check names, declared pass/fail/not-tested results, byte lengths,
SHA-256 fingerprints, explicit limitations and an unverified local creation time.
It omits evidence contents and paths. Names and hashes can still reveal or link
information: inspect the file before deliberately sharing it. Keep original
private evidence so another person can compare the bytes you choose to provide.

The check command compares the statement’s declared fields with the input and
detects changed evidence bytes. The local creation date is unauthenticated; the
command cannot establish who made a declaration or when. It **does not rerun
your tests, verify the declared source revision, or establish that a declared
result is truthful**.
`all_declared_checks_pass` is false if any check failed or was not tested. Even
when true, `certification`, `mark_authorization`, `independent_accuracy_validated`
and `signature_verified` stay false. Unknown fields, missing limits, duplicate
check names, fabricated certification fields and unsafe files are refused.

## Future certification is a different decision

A future programme needs adopted standards, an accountable mark holder, actual
certifier qualifications, impartial decisions, appeals and explicit licenses.
It must not turn these self-declarations into approval automatically. The
[USPTO's certification-mark guidance](https://www.uspto.gov/trademarks/apply/certification-mark-applications)
distinguishes certification of others' goods/services from ordinary branding.
F-143 and F-145 remain open; this tool does not file, license or operate either.
The project name's clearance question remains separate.

These guidelines and template complete the document/tool job F-144. They do not
represent a lawyer's clearance opinion or an operating certification programme.
