#!/usr/bin/env python3
"""Run the adjudicator against the documented real-world failure cases.

    python3 scripts/demo-adjudication.py

No arguments, no network, no dependencies. Prints what our verdict lattice says
about cases where shipped products are documented to say something false, so
the difference is observable rather than asserted.

Sources for every case are printed with it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(path: str):
    name = path.replace("/", "_").replace(".py", "")
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


V = _load("services/adjudicator/verdict.py")
A = _load("services/adjudicator/adjudicate.py")
M = _load("eval/measure.py")

BAR = "=" * 78


def head(n: int, title: str, source: str) -> None:
    print(f"\n{BAR}\nCASE {n}  {title}\n          source: {source}\n{BAR}")


def show_verdict(label: str, v) -> None:
    flag = "ASSERTABLE" if v.is_asserted else "NOT ASSERTABLE"
    print(f"\n  {label}")
    print(f"    state       : {v.state}")
    print(f"    integrity   : {v.integrity.name}")
    print(f"    revocation  : {v.revocation.value}  (known={v.revocation.is_known})")
    print(f"    -> {flag}")
    print(f"    message     : {v.render()}")


def show_adjudication(label: str, a) -> None:
    print(f"\n  {label}")
    print(f"    outcome     : {a.outcome.value}   (rule {a.rule})")
    print(f"    value       : {a.value!r}")
    if a.contradiction:
        for value, sources in a.contradiction:
            print(f"    contradiction: {value!r} per {', '.join(sources)}")
    if a.overruled:
        for s in a.overruled:
            print(f"    overruled   : {s.layer.label}={s.value!r} ({s.source})")
    print(f"    message     : {a.render()}")


def main() -> int:
    print("SIMULATED INPUTS ONLY: no media, signature, watermark or OCSP is verified by this demo.")
    # -------------------------------------------------------------------
    head(
        1,
        "Revoked certificate, intact bytes (the Nikon Z6 III case)",
        "Golaszewski et al., arXiv:2604.24890 / IACR ePrint 2026/804",
    )
    print(
        "\n  A Nikon Z6 III signing certificate was revoked in November 2025.\n"
        "  Six months later, on the same file:\n"
        "      Adobe Inspect  -> reported the signature VALID\n"
        "      Verifieddit    -> reported the file INVALID\n"
        '      paper          -> "Neither conforming validator reports the revocation."\n'
        "\n  Our lattice, in both validator postures:"
    )
    show_verdict(
        "posture A — validator did not check (c2pa-rs default ocsp_fetch=false)",
        V.from_status_codes(
            ["claimSignature.validated", "signingCredential.trusted", "assertion.dataHash.match"],
            ocsp_checked=False,
        ),
    )
    show_verdict(
        "posture B — validator checked and found the revocation",
        V.from_status_codes(
            ["claimSignature.validated", "signingCredential.trusted", "assertion.dataHash.match", "signingCredential.ocsp.revoked"]
        ),
    )
    print(
        "\n  Neither posture can be shown as a pass. Constraint V2 forbids it:\n"
        "  VALID + unknown revocation is a measurement we declined to take."
    )

    # -------------------------------------------------------------------
    head(
        2,
        "Revoked is not Tampered",
        "Verifieddit hasFatalValidation() renders both as 'altered after signing'",
    )
    show_verdict("revoked credential, bytes intact",
                 V.from_status_codes(["signingCredential.ocsp.revoked"]))
    show_verdict("hard binding mismatch, bytes changed",
                 V.from_status_codes(["assertion.dataHash.mismatch"]))
    print(
        "\n  Two different facts, two different sentences. Telling a user their\n"
        "  file was altered when the real problem is a withdrawn credential is a\n"
        "  false statement about the content."
    )

    # -------------------------------------------------------------------
    head(
        3,
        "The authenticated fake",
        "Nemecek et al., arXiv:2603.02378 — 'No deployed system adjudicates between them.'",
    )
    print(
        "\n  A VALID manifest asserts human authorship. The pixels carry an\n"
        "  AI-generation watermark. No cryptography is broken; one permitted\n"
        "  assertion was omitted."
    )
    manifest = A.Signal(
        A.Layer.MANIFEST, "origin", "human", "c2pa:manifest/urn:uuid:...",
        verdict_state="valid", verified=True,
    )
    watermark = A.Signal(A.Layer.WATERMARK, "origin", "ai", "trustmark:com.adobe.trustmark.Q", verified=True)
    show_adjudication("manifest(human) vs watermark(ai)",
                      A.adjudicate([manifest, watermark], claim="origin"))
    print(
        "\n  MANIFEST and WATERMARK hold equal standing by design, so the\n"
        "  disagreement is irreducible. We name both sides instead of picking a\n"
        "  winner we have no authority to pick."
    )

    # -------------------------------------------------------------------
    head(
        4,
        "The same fake, but the signature was also revoked",
        "standing forfeiture, spec section 2.3",
    )
    revoked_manifest = A.Signal(
        A.Layer.MANIFEST, "origin", "human", "c2pa:manifest/urn:uuid:...",
        verdict_state="revoked", verified=True,
    )
    print(f"\n  manifest standing: {revoked_manifest.standing} (forfeited from "
          f"{A.Layer.MANIFEST.standing})")
    show_adjudication("revoked manifest(human) vs watermark(ai)",
                      A.adjudicate([revoked_manifest, watermark], claim="origin"))
    print("\n  The stronger finding absorbs the weaker one. No false contradiction.")

    # -------------------------------------------------------------------
    head(
        5,
        "A classifier at confidence 1.0 cannot overrule a signed assertion",
        "Liang et al. arXiv:2304.02819 (61.22% FPR on TOEFL); "
        "Khvatskii et al. arXiv:2608.11256",
    )
    show_adjudication(
        "manifest(human) vs classifier(ai, confidence=1.0)",
        A.adjudicate(
            [
                manifest,
                A.Signal(A.Layer.CLASSIFIER, "origin", "ai", "local-probe",
                         confidence=1.0),
            ],
            claim="origin",
        ),
    )
    show_adjudication(
        "classifier alone at confidence 0.99",
        A.adjudicate(
            [A.Signal(A.Layer.CLASSIFIER, "origin", "ai", "local-probe",
                      confidence=0.99)],
            claim="origin",
        ),
    )
    print(
        "\n  Detector FPRs are demographically structured — 61.22% on TOEFL\n"
        "  essays, 25.3% non-STEM vs 5.6% STEM at paper level (p=0.0002).\n"
        "  A surrogate that could overrule a signature would inherit those\n"
        "  error rates as authority."
    )

    # -------------------------------------------------------------------
    head(
        6,
        "Absence is not a negative finding",
        "Google Gemini help copy vs Google's own SynthID portal copy",
    )
    show_verdict("no manifest at all", V.from_status_codes([], manifest_present=False))
    print(
        '\n  Google Gemini help: if a watermark "isn\'t detected, it means the\n'
        '  image or video wasn\'t created or edited by Google AI".\n'
        '  Google SynthID portal: it "is unlikely that this media was made with\n'
        '  AI from a SynthID partner".\n'
        "  Two standards for the same watermark on the same vendor's surfaces.\n"
        "  Rule R1 and the UNSIGNED state exist so our copy cannot drift there."
    )

    # -------------------------------------------------------------------
    head(
        7,
        "Measurement: a perfect score on n=1 is not certainty",
        "eval/measure.py — Wilson score interval, not the normal approximation",
    )
    results = [
        M.FixtureResult(
            "nikon-z6iii-revoked-nov2025",
            {"adobe-inspect": "valid", "verifieddit": "tampered", "ours": "revoked"},
            expected="revoked",
        )
    ]
    print(f"\n  fixture classification: {results[0].classification.value}")
    for name, iv in sorted(M.per_validator_accuracy(results).items()):
        print(f"    {name:16s} accuracy {iv}")
    print(
        "\n  Our validator is right and still cannot claim certainty: the honest\n"
        "  interval on 1/1 is wide. The normal approximation would have printed\n"
        "  100% +/- 0%, which is the shape of an unfalsifiable claim."
    )
    print("\n  Study design — uploads needed per platform for a given interval width:")
    for width in (0.30, 0.20, 0.10, 0.05):
        print(f"    +/-{width:.0%} -> n = {M.min_trials_for_width(width):>5d}")

    print(f"\n{BAR}")
    print("All of the above is deterministic, offline, and covered by")
    print("tests/test_adjudicator.py (49 tests). Rules: docs/adjudication-spec.md")
    print(BAR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
