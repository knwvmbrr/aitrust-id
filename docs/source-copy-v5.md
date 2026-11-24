# Check a finite source-copy selection

V5 checks a committed descendant of protected898dc254ff8d4c924d699afe732d3c1bbfe1bb01 against a fixed installed policy and all mandatory baseline files. It does not authenticate a received artifact or approve runtime, SDK, model, native library, accuracy or every distribution route.

Use an independently selected trusted checkout. The CLI has no allow flag or caller-selected policy:

```sh
python3 -I -S -B tools/source_release_policy_v5.py --help
python3 -I -S -B tools/source_release_policy_v5.py --source-commit FULL_COMMIT_OID
python3 -I -S -B tools/source_release_policy_v5.py --source-commit FULL_COMMIT_OID --archive /private/owned/source.tar.gz
```

The first command is informational. The latter commands emit one JSON result, exit0 only on the selected finite check's success, or exit2 with UNAVAILABLE and a bounded reason. The archive form additionally binds every canonical archive byte/member to trusted Git. Its signature_verified and release_authorized remain false. Obtain and verify protected producer authenticity through the separately reviewed managed-source consumer; a supplied archive or evidence packet cannot choose trust roots or its policy.

Python callers use verify(root=ROOT,source_commit=...) and verify_archive(raw,source_commit=...). Each result preserves source_copy_profile_satisfied and all explicit false claims. The installed root, table and foundations are pinned and recaptured. Concurrent threads or an existing alarm are unsupported and refuse rather than altering another caller's timer. File paths with symlink ancestry, nonregular files and unsupported Git entries refuse.

All baseline files are mandatory; only exact named first-party changes with retained declaration markers or exact named copied data with complete carried anchors can pass. The mixed tokenizer record retains source-carried and supplemental terms separately from its genuinely empty wheel-carried notice array. It never asserts that all package features were compiled or that an entire wheel is cleared.

The component's small controls establish software boundaries only. Full current committed-source/archive qualification, registry activation, protected producer and fresh consumer execution remain ROOT integration work. No original requirement or tag validation is closed by these controls.
