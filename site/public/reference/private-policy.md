# Try a team-selected term check — offline development tool

Choose a policy, review its terms, then check a text file on your computer.
For example, a fictional team can look for the phrase “confidential draft.” A
match tells you that the phrase occurs. It does **not** say that someone broke a
rule, that a document is safe, or that AI Trust ID certified the result.

This optional open-source component runs separately from personal tags. It
doesn't change PS, hide public evidence, require a receipt, upload text or enroll
you in research. It has no account or subscription. An enterprise service and
official organization namespaces are still proposals.

## Practice in three steps

Download and unzip the [repository](https://github.com/knwvmbrr/aitrust-id/archive/refs/heads/main.zip).
Open Terminal in that folder. Python 3.12 or later is required; this component
needs no extra package or model download.

1. Create a private practice folder outside the repository:

```sh
practice="$(mktemp -d "${TMPDIR:-/tmp}/aitrust-policy.XXXXXXXX")"
python3 scripts/prepare-private-policy-demo.py --output "$practice/demo"
```

2. Read the invented policy in `$practice/demo/policy.json`. It selects one
   phrase and uses the unverified example namespace `example-team`.
3. If you choose to run this local practice check:

```sh
python3 scripts/check-private-policy.py --packet "$practice/demo" --reviewed-policy
```

The short answer reports the number of selected phrase occurrences. It omits
your text, organization namespace, fingerprints and locations. No result is
automatically saved or sent anywhere.

## See the locations — only if you want them

Add `--details "$practice/details"` to the check command. A new private folder
contains `private-policy-observations.json`: the qualified private code,
locations, method/policy/text fingerprints and explicit limits. It contains no
complete source text. Fingerprints and locations may still reveal or link
information. Keep this file private and share deliberately. Existing folders
are never overwritten.

Remove your practice folder to delete its inputs and any results you explicitly
saved. There is no background service to uninstall. Personal checks continue
to work without this optional component.

## Use your own policy — advanced

Keep `subject.txt`, `policy.json` and `selection.json` in an owner-held `700`
folder outside the repository, with regular singly linked `600` files. Save
text as UTF-8. The invented packet shows the entire profile; unknown fields are
refused. A policy has its own namespace, ID and revision. Its claim is fixed to
literal occurrence. Limits must be visible, receipts optional and personal
checks separate. No public thresholds, public meanings, capture permission,
upload setting, custom claim labels or public tag codes are accepted.

The selection binds the policy's exact raw SHA-256, namespace and the subject's
frozen NFC SHA-256. Changing either file requires a new reviewed selection.
This binds the chosen files; it does not prove namespace ownership, employee
consent or organizational authority.

Only case-sensitive ASCII phrases with ASCII word boundaries are supported.
There are at most 32 rules, 8 phrases per rule, 128 characters per phrase and
20,000 input code points. At most 64 locations are returned, with an explicit
truncation flag and total count if there are more. These bounds are not an
accuracy claim. No match establishes compliance. Unsupported policy, stale
selection, unsafe file access and invalid input return **Unavailable**, exit
`2`, without a partial result.

A modified checkout or compromised same-account process/administrator can
bypass local protections. This component cannot prevent an employer from
coercing someone outside the tool. No commercial conformance or organizational
security claim is made.

## Recheck the command

```sh
python3 scripts/verify-private-policy.py --python "$(command -v python3)" --output output/verification/private-policy-controls.json
```

The controls use invented examples and do not measure compliance, real-world
accuracy or human consent. [Full scope](scope-progress.md) remains visible.
