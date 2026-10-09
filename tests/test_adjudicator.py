"""Tests for the verdict lattice, the conflict adjudicator and measurement.

Each test names the invariant it protects and, where the invariant exists
because of a documented real-world failure, cites it. Several tests are
regressions against failures that shipped in other people's products.
"""

import importlib.util
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(path):
    """Load a repo module by path, matching the convention in the other tests.

    One addition over the shorter helper used elsewhere: the module is
    registered in `sys.modules` *before* execution. `dataclasses` resolves
    `cls.__module__` through `sys.modules` when it sees a `field(...)` default,
    so an unregistered module raises AttributeError on import. Keep the
    registration if you copy this helper.
    """
    name = path.replace("/", "_").replace(".py", "")
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


V = module("services/adjudicator/verdict.py")
A = module("services/adjudicator/adjudicate.py")
M = module("eval/measure.py")

#: The three positive codes that together establish verification, per
#: verdict._complete_verification(). Supplying fewer yields UNVERIFIED, not
#: VALID -- "nothing failed" is not "everything checked". These fixtures
#: originally supplied only two of the three and were therefore asserting a
#: pass on an incomplete result set; corrected 2026-10-09.
COMPLETE = [
    "claimSignature.validated",
    "signingCredential.trusted",
    "assertion.dataHash.match",
]


# =========================================================================
# VERDICT LATTICE
# =========================================================================


def test_revoked_is_not_reported_as_tampered():
    """Regression against Verifieddit's shipped behaviour.

    Its `hasFatalValidation()` treats every code not ending in '.untrusted' or
    '.expired' as fatal and renders them behind one label reading "altered
    after signing". A revoked credential is therefore reported as byte
    tampering — a different and false claim. Here they are distinct states with
    distinct sentences.
    """
    revoked = V.from_status_codes(["signingCredential.ocsp.revoked"])
    tampered = V.from_status_codes(["assertion.dataHash.mismatch"])

    assert revoked.integrity is V.Integrity.REVOKED
    assert tampered.integrity is V.Integrity.TAMPERED
    assert revoked.state != tampered.state
    assert "revoked by its issuer" in revoked.render()
    assert "verification failed" in tampered.render()
    # And it must not attribute the difference to anyone or anything.
    assert "does not establish when, why, or by whom" in tampered.render()
    # The revoked case must not claim the content failed its binding.
    assert "verification failed" not in revoked.render()


def test_the_nikon_case_cannot_be_reported_as_valid():
    """Regression against the documented Adobe Inspect / Verifieddit failure.

    Golaszewski, Krawetz, Sherman et al. (arXiv:2604.24890) found a Nikon
    Z6 III certificate revoked in November 2025 still reported valid by Adobe
    Inspect six months later: "Neither conforming validator reports the
    revocation."

    The file validates cryptographically — the signature is intact and the
    signer chains to a trust anchor. The ONLY thing wrong is revocation. A
    validator that does not check therefore sees a clean file. This asserts that
    our lattice cannot produce an unqualified pass in either posture.
    """
    # Posture 1: the validator did not check (c2pa-rs default ocsp_fetch=false).
    unchecked = V.from_status_codes(COMPLETE, ocsp_checked=False)
    assert unchecked.integrity is V.Integrity.VALID
    assert unchecked.revocation is V.Revocation.UNKNOWN_SKIPPED
    assert unchecked.is_asserted is False, (
        "a valid signature with unchecked revocation must never be assertable"
    )
    assert unchecked.state == "valid_revocation_unknown"
    assert "NOT checked" in unchecked.render()

    # Posture 2: the validator did check, and found the revocation.
    checked = V.from_status_codes(
        COMPLETE + ["signingCredential.ocsp.revoked"]
    )
    assert checked.integrity is V.Integrity.REVOKED
    assert checked.revocation is V.Revocation.REVOKED
    assert checked.is_asserted is False


def test_unknown_revocation_is_never_silently_optimistic():
    """The default posture when nothing speaks to revocation is UNKNOWN.

    c2pa-rs defines `signingCredential.ocsp.skipped` as "The validator chose
    not to perform an online OCSP check" — a fact about the validator, not the
    asset. Defaulting to NOT_REVOKED would launder that into an assurance.
    """
    silent = V.from_status_codes(["claimSignature.validated"])
    assert silent.revocation is V.Revocation.UNKNOWN_SKIPPED
    assert silent.is_asserted is False


def test_only_a_checked_valid_verdict_is_assertable():
    ok = V.from_status_codes(COMPLETE + ["signingCredential.ocsp.notRevoked"])
    assert ok.integrity is V.Integrity.VALID
    assert ok.revocation is V.Revocation.NOT_REVOKED
    assert ok.is_asserted is True
    assert ok.state == "valid"


@pytest.mark.parametrize(
    "code,expected",
    [
        ("signingCredential.ocsp.skipped", "UNKNOWN_SKIPPED"),
        ("signingCredential.ocsp.inaccessible", "UNKNOWN_INACCESSIBLE"),
    ],
)
def test_the_two_unknown_states_are_distinguishable(code, expected):
    """"I didn't look" and "I looked and couldn't tell" are different facts.

    No shipped reader in the category surfaces either one.
    """
    v = V.from_status_codes(["claimSignature.validated", code])
    assert v.revocation.name == expected
    assert v.revocation.is_known is False
    assert v.is_asserted is False


def test_unsigned_is_not_a_negative_finding():
    """Absence of a credential carries no information, and the copy must say so.

    This is the error in Google's own Gemini help text, which states that if a
    watermark "isn't detected, it means the image or video wasn't created or
    edited by Google AI" — while Google's SynthID portal says only that it "is
    unlikely that this media was made with AI from a SynthID partner".
    """
    v = V.from_status_codes([], manifest_present=False)
    assert v.integrity is V.Integrity.UNSIGNED
    assert v.revocation is V.Revocation.NOT_APPLICABLE
    assert v.is_asserted is False
    msg = v.render()
    assert "not evidence the content is fake" in msg
    assert "not evidence it is genuine" in msg


def test_absent_manifest_with_codes_is_a_programming_error():
    with pytest.raises(ValueError, match="cannot produce validation codes"):
        V.from_status_codes(["claimSignature.validated"], manifest_present=False)


def test_unmapped_code_raises_rather_than_passing():
    """An unrecognised code must never be read as success.

    Treating unknown codes as benign is the mechanism by which a validator
    silently inherits a new failure mode as a pass.
    """
    with pytest.raises(V.UnmappedStatusCode, match="Refusing to guess"):
        V.from_status_codes(["signingCredential.someFutureFailure"])

    lenient = V.from_status_codes(
        ["signingCredential.someFutureFailure"], strict=False
    )
    assert any("not recognised" in n for n in lenient.notes)
    # Lenient mode still must not assert — there is an uninterpreted failure.
    assert lenient.revocation.is_known is False


def test_severity_ordering_picks_the_worst_finding():
    v = V.from_status_codes(
        [
            "signingCredential.expired",
            "assertion.dataHash.mismatch",
            "signingCredential.untrusted",
        ]
    )
    assert v.integrity is V.Integrity.TAMPERED


def test_conflict_is_its_own_state_not_an_error():
    """C2PA 8.2 treats manifest conflict as identifier re-labelling; we don't.

    Security Considerations 2.4 2.1: "Details on how one determines which C2PA
    Manifest is the origin are left for specification."
    """
    for code in (
        "claim.multiple",
        "assertion.multipleHardBindings",
        "manifest.multipleParents",
    ):
        v = V.from_status_codes([code])
        assert v.integrity is V.Integrity.CONFLICTED, code
        assert "disagree" in v.render()


def test_a_positive_revocation_finding_cannot_be_overridden():
    """The REVOKED pair is never decoupled, from either direction.

    Two attack surfaces on the same invariant: a caller asserting it checked
    and found nothing, and a status set containing both codes. Neither may
    launder a revoked credential into a clean one.
    """
    # Caller says "I checked, it's fine" over a positive revoked code.
    v = V.from_status_codes(["signingCredential.ocsp.revoked"], ocsp_checked=True)
    assert v.revocation is V.Revocation.REVOKED
    assert v.integrity is V.Integrity.REVOKED
    assert v.is_asserted is False

    # Contradictory codes: the positive finding wins.
    v = V.from_status_codes(
        ["signingCredential.ocsp.notRevoked", "signingCredential.ocsp.revoked"]
    )
    assert v.revocation is V.Revocation.REVOKED
    assert v.integrity is V.Integrity.REVOKED

    # Order-independent.
    v = V.from_status_codes(
        ["signingCredential.ocsp.revoked", "signingCredential.ocsp.notRevoked"]
    )
    assert v.revocation is V.Revocation.REVOKED


def test_the_integrity_revocation_pair_is_guarded_not_derived():
    """REVOKED integrity without a REVOKED finding must fail loudly.

    The guard is only reachable by a mapping that sets REVOKED integrity
    without the matching revocation code — exactly what a future careless edit
    to _INTEGRITY_CODES would do. Simulated here so the guard itself is tested
    rather than merely present.
    """
    import unittest.mock as mock

    with mock.patch.dict(
        V._INTEGRITY_CODES, {"x.fake": V.Integrity.REVOKED}, clear=False
    ):
        with pytest.raises(ValueError, match="must never be inferred"):
            V.from_status_codes(["x.fake"], ocsp_checked=True)


def test_worst_combines_manifests_without_averaging_away_doubt():
    good = V.from_status_codes(COMPLETE + ["signingCredential.ocsp.notRevoked"])
    unknown = V.from_status_codes(COMPLETE, ocsp_checked=False)
    combined = V.worst([good, unknown])
    assert combined.is_asserted is False, (
        "one manifest with unknown revocation must taint the asset's verdict"
    )

    revoked = V.from_status_codes(["signingCredential.ocsp.revoked"])
    assert V.worst([good, revoked]).integrity is V.Integrity.REVOKED


def test_every_integrity_state_has_plain_language():
    for state in V.Integrity:
        assert V._PLAIN_LANGUAGE[state].strip(), state
    for state in V.Revocation:
        assert state in V._REVOCATION_LANGUAGE, state


def test_render_never_omits_an_unknown_revocation():
    """The structural promise of this module, asserted directly."""
    for code in ("signingCredential.ocsp.skipped", "signingCredential.ocsp.inaccessible"):
        v = V.from_status_codes(["claimSignature.validated", code])
        assert "would look identical" in v.render(), code


# =========================================================================
# CONFLICT ADJUDICATION
# =========================================================================


def _manifest(value, source="c2pa-manifest", state="valid", verified=True):
    return A.Signal(A.Layer.MANIFEST, "origin", value, source,
                    verdict_state=state, verified=verified)


def _watermark(value, source="trustmark", verified=True):
    """verified=True means the soft binding was decoded AND resolved to a
    manifest that validated — not merely that a payload was decoded."""
    return A.Signal(A.Layer.WATERMARK, "origin", value, source, verified=verified)


def _classifier(value, conf, source="local-probe"):
    return A.Signal(A.Layer.CLASSIFIER, "origin", value, source, confidence=conf)


def test_the_authenticated_fake_is_reported_as_contradicted():
    """The case Nemecek et al. (arXiv:2603.02378) say nobody adjudicates.

    A valid manifest asserts human authorship; the pixels carry an AI
    watermark. Their finding on the two competing claims: "No deployed system
    adjudicates between them." We neither pick a winner nor call it an error.
    """
    result = A.adjudicate(
        [_manifest("human"), _watermark("ai")], claim="origin"
    )
    assert result.outcome is A.Outcome.CONTRADICTED
    assert result.rule == "R3"
    assert result.value is None
    assert result.is_asserted is False
    # Both sides must be named, with their sources.
    values = {v for v, _ in result.contradiction}
    assert values == {"human", "ai"}
    assert "CONTRADICTED" in result.render()
    assert "trustmark" in result.render()


def test_a_classifier_can_never_contradict_an_intentional_signal():
    """Even at confidence 1.0.

    Classifier FPRs are demographically structured: 61.22% on TOEFL essays
    (Liang et al., arXiv:2304.02819) and 25.3% vs 5.6% non-STEM/STEM at the
    paper level (Khvatskii et al., arXiv:2608.11256, permutation p = 0.0002).
    A surrogate that can overrule a signed assertion would inherit those error
    rates as authority.
    """
    result = A.adjudicate(
        [_manifest("human"), _classifier("ai", 1.0)], claim="origin"
    )
    assert result.outcome is A.Outcome.SUPPORTED
    assert result.value == "human"
    assert result.rule == "R2"


def test_a_classifier_alone_never_establishes_a_claim():
    result = A.adjudicate([_classifier("ai", 0.99)], claim="origin")
    assert result.outcome is A.Outcome.UNSUPPORTED
    assert result.rule == "R5"
    assert result.is_asserted is False


def test_unsigned_metadata_loses_to_a_manifest_but_is_recorded():
    """R4: a signed manifest strictly outranks unsigned EXIF — and the EXIF
    disagreement is kept in the record rather than discarded, because "the
    metadata says something else" is worth showing even though it settles
    nothing."""
    exif = A.Signal(A.Layer.METADATA, "origin", "human", "exif:Artist")
    result = A.adjudicate([_manifest("ai"), exif], claim="origin")
    assert result.outcome is A.Outcome.SUPPORTED
    assert result.value == "ai"
    assert result.rule == "R4"
    assert result.overruled == (exif,)
    assert result.to_dict()["overruled"][0]["source"] == "exif:Artist"


def test_unsigned_metadata_alone_establishes_nothing():
    """Metadata contests but cannot assert — the two thresholds, demonstrated."""
    exif = A.Signal(A.Layer.METADATA, "origin", "human", "exif:Artist")
    assert exif.may_contest is True
    assert exif.may_assert is False
    result = A.adjudicate([exif], claim="origin")
    assert result.outcome is A.Outcome.UNSUPPORTED
    assert result.rule == "R5"


def test_agreeing_metadata_cannot_manufacture_an_assertion():
    """Two agreeing weak signals are still not an assertion.

    R5 is ordered before the comparison rules precisely so that stacking
    unsigned sources cannot add up to standing nobody had.
    """
    result = A.adjudicate(
        [
            A.Signal(A.Layer.METADATA, "origin", "human", "exif:Artist"),
            A.Signal(A.Layer.METADATA, "origin", "human", "xmp:Creator"),
            _classifier("human", 0.99),
        ],
        claim="origin",
    )
    assert result.outcome is A.Outcome.UNSUPPORTED
    assert result.rule == "R5"


def test_no_signal_is_unsupported_not_clean():
    result = A.adjudicate([], claim="origin")
    assert result.outcome is A.Outcome.UNSUPPORTED
    assert result.rule == "R1"
    assert "absence of a signal is not evidence of the opposite" in result.render()


def test_a_non_assertable_manifest_forfeits_standing():
    """A revoked manifest does not get to win an argument.

    This is the join with verdict.py: an authenticated fake whose signature was
    also revoked collapses to the simpler revoked answer rather than presenting
    as an irreducible contradiction.
    """
    revoked_manifest = _manifest("human", state="revoked")
    assert revoked_manifest.standing == 0
    result = A.adjudicate([revoked_manifest, _watermark("ai")], claim="origin")
    assert result.outcome is A.Outcome.SUPPORTED
    assert result.value == "ai"
    assert result.rule == "R2"


def test_valid_revocation_unknown_manifest_also_forfeits():
    unknown = _manifest("human", state="valid_revocation_unknown")
    assert unknown.standing == 0


def test_agreeing_signals_are_supported():
    result = A.adjudicate([_manifest("ai"), _watermark("ai")], claim="origin")
    assert result.outcome is A.Outcome.SUPPORTED
    assert result.value == "ai"
    assert result.rule == "R2"


def test_three_way_contradiction_names_all_three():
    result = A.adjudicate(
        [
            _manifest("human", source="m1"),
            _watermark("ai", source="w1"),
            _watermark("ai_assisted", source="w2"),
        ],
        claim="origin",
    )
    assert result.outcome is A.Outcome.CONTRADICTED
    assert len(result.contradiction) == 3


def test_signals_require_attribution():
    with pytest.raises(ValueError, match="not evidence"):
        A.Signal(A.Layer.WATERMARK, "origin", "ai", "", verified=False)


def test_assertion_capable_signals_must_state_verified_explicitly():
    """Regression for a dangerous default. `verified` previously defaulted to
    False, so a caller unaware of the field silently lost all standing and
    every claim fell to R5 UNSUPPORTED with nothing explaining why."""
    for layer in (A.Layer.MANIFEST, A.Layer.WATERMARK):
        with pytest.raises(ValueError, match="must state `verified` explicitly"):
            A.Signal(layer, "origin", "ai", "src", verdict_state="valid")


def test_verified_is_rejected_where_it_is_meaningless():
    with pytest.raises(ValueError, match="meaningless for"):
        A.Signal(A.Layer.METADATA, "origin", "ai", "exif", verified=True)


def test_an_unverified_watermark_carries_no_standing():
    """A decoded payload is a pointer, not an assertion. Perceptual-hash
    collisions are a documented attack, so a bare hit cannot assert."""
    assert _watermark("ai", verified=False).standing == 0
    assert A.adjudicate([_watermark("ai", verified=False)], claim="origin").rule == "R5"


def test_classifier_requires_a_confidence():
    with pytest.raises(ValueError, match="not reportable"):
        A.Signal(A.Layer.CLASSIFIER, "origin", "ai", "probe")


def test_confidence_bounds_are_enforced():
    with pytest.raises(ValueError, match=r"\[0,1\]"):
        A.Signal(A.Layer.CLASSIFIER, "origin", "ai", "probe", confidence=1.5)


def test_claims_are_adjudicated_independently():
    signals = [
        _manifest("human"),
        _watermark("ai"),
        A.Signal(A.Layer.MANIFEST, "capture_device", "nikon-z6iii", "m1", verdict_state="valid", verified=True),
    ]
    out = A.adjudicate_all(signals)
    assert out["origin"].outcome is A.Outcome.CONTRADICTED
    assert out["capture_device"].outcome is A.Outcome.SUPPORTED


def test_adjudication_is_deterministic():
    signals = [_manifest("human"), _watermark("ai")]
    first = A.adjudicate(signals, claim="origin").to_dict()
    for _ in range(20):
        assert A.adjudicate(list(reversed(signals)), claim="origin").to_dict()[
            "contradiction"
        ] == first["contradiction"]


def test_every_rule_is_documented():
    """A rule that fires but is not published cannot be contested."""
    fired = {"R1", "R2", "R3", "R4", "R5"}
    for rule in fired:
        assert rule in A.RULES_DOC, f"{rule} fires in code but is not in RULES_DOC"


# =========================================================================
# MEASUREMENT
# =========================================================================


def test_wilson_has_no_degenerate_interval_at_the_extremes():
    """The reason we do not use the normal approximation.

    Wald gives zero width at k=0 and k=n, which would let a 10-sample run
    report "0% survival, +/-0%" — an unfalsifiable claim.
    """
    zero = M.wilson(0, 10)
    full = M.wilson(10, 10)
    assert zero.point == 0.0 and zero.width > 0.25
    assert full.point == 1.0 and full.width > 0.25
    assert zero.low == 0.0 and full.high == 1.0


def test_wilson_stays_inside_the_unit_interval():
    for n in (1, 2, 3, 7, 10, 50, 1000):
        for k in range(n + 1):
            iv = M.wilson(k, n)
            assert 0.0 <= iv.low <= iv.point <= iv.high <= 1.0, (k, n)


def test_wilson_matches_published_values():
    """Spot-check against the textbook result for 95%, k=0, n=10."""
    iv = M.wilson(0, 10, 0.95)
    assert math.isclose(iv.high, 0.2775, abs_tol=5e-4), iv.high
    iv = M.wilson(1, 10, 0.95)
    assert math.isclose(iv.low, 0.0179, abs_tol=5e-4), iv.low
    assert math.isclose(iv.high, 0.4041, abs_tol=5e-4), iv.high


def test_wilson_narrows_with_n():
    widths = [M.wilson(n // 2, n).width for n in (10, 100, 1000, 10000)]
    assert widths == sorted(widths, reverse=True)


def test_interval_rejects_impossible_counts():
    with pytest.raises(ValueError, match="trials must be positive"):
        M.wilson(0, 0)
    with pytest.raises(ValueError, match="successes must be in"):
        M.wilson(11, 10)


def test_z_for_known_and_interpolated_levels():
    assert math.isclose(M.z_for(0.95), 1.959963984540054, abs_tol=1e-12)
    assert math.isclose(M.z_for(0.975), 2.2414, abs_tol=1e-3)


def test_min_trials_answers_the_study_design_question():
    """How many uploads per platform? Worst case p=0.5."""
    n = M.min_trials_for_width(0.20)
    assert 90 < n < 110, n
    assert M.wilson(n // 2, n).width <= 0.20
    assert M.min_trials_for_width(0.10) > n


def test_disagreement_matrix_counts_only_mutual_answers():
    """A validator that crashes often must not get a flattering rate."""
    results = [
        M.FixtureResult("f1", {"a": "valid", "b": "revoked"}),
        M.FixtureResult("f2", {"a": "valid", "b": None}),
        M.FixtureResult("f3", {"a": "valid", "b": "valid"}),
    ]
    matrix = M.disagreement_matrix(results)
    iv = matrix[("a", "b")]
    assert iv.trials == 2, "f2 must be excluded — b did not answer"
    assert iv.successes == 1


def test_the_nikon_disagreement_is_representable_end_to_end():
    """The documented Adobe Inspect / Verifieddit split, as a graded fixture.

    Expected state is the honest one: the credential was revoked, so neither
    'valid' nor a bare 'tampered' is correct.
    """
    results = [
        M.FixtureResult(
            "nikon-z6iii-revoked-nov2025",
            {"adobe-inspect": "valid", "verifieddit": "tampered", "ours": "revoked"},
            expected="revoked",
        )
    ]
    assert results[0].classification is M.Disagreement.SPLIT
    acc = M.per_validator_accuracy(results)
    assert acc["ours"].point == 1.0
    assert acc["adobe-inspect"].point == 0.0
    assert acc["verifieddit"].point == 0.0
    # And even a perfect score on n=1 must report an honest interval.
    assert acc["ours"].low < 0.9, (
        "n=1 must not be reportable as certainty — got "
        f"{acc['ours']}"
    )


def test_incomplete_is_distinguished_from_split():
    assert (
        M.FixtureResult("f", {"a": "valid", "b": None}).classification
        is M.Disagreement.INCOMPLETE
    )
    assert (
        M.FixtureResult("f", {"a": "valid", "b": "valid"}).classification
        is M.Disagreement.UNANIMOUS
    )


def test_ungraded_fixtures_measure_agreement_not_correctness():
    r = M.FixtureResult("f", {"a": "valid", "b": "valid"})
    assert r.correct is None
    assert M.per_validator_accuracy([r]) == {}


def test_summarize_is_json_shaped_and_diffable():
    import json

    results = [
        M.FixtureResult("f1", {"a": "valid", "b": "revoked"}, expected="revoked"),
        M.FixtureResult("f2", {"a": "valid", "b": "valid"}, expected="valid"),
    ]
    out = M.summarize(results)
    assert json.loads(json.dumps(out)) == out
    assert out["fixtures"] == 2
    assert out["graded_fixtures"] == 2
    assert out["validators"] == ["a", "b"]
    assert out["classification_counts"]["split"] == 1


def test_survival_reports_manifest_and_soft_binding_separately():
    """A platform that strips manifests but keeps soft bindings is the whole
    case for durable bindings, and it is invisible if you measure one column."""
    trials = [
        M.SurvivalTrial("platform-x", f"f{i}", manifest_survived=False,
                        soft_binding_survived=True)
        for i in range(20)
    ]
    rates = M.survival_rates(trials)["platform-x"]
    assert rates["manifest"].point == 0.0
    assert rates["soft_binding"].point == 1.0
    assert rates["manifest"].width > 0.0, "zero survival still needs an interval"


def test_survival_soft_binding_is_none_when_unmeasured():
    trials = [M.SurvivalTrial("p", "f", manifest_survived=True)]
    assert M.survival_rates(trials)["p"]["soft_binding"] is None


# =========================================================================
# INTEGRATION: the two modules compose
# =========================================================================


def test_verdict_state_feeds_adjudication_standing():
    """The documented seam between the modules.

    verdict.Verdict.state is exactly what Signal.verdict_state expects, so a
    manifest's own validation outcome governs whether it carries standing.
    """
    assertable = V.from_status_codes(COMPLETE + ["signingCredential.ocsp.notRevoked"])
    unchecked = V.from_status_codes(COMPLETE, ocsp_checked=False)

    strong = A.Signal(
        A.Layer.MANIFEST, "origin", "human", "m", verdict_state=assertable.state, verified=True
    )
    weak = A.Signal(
        A.Layer.MANIFEST, "origin", "human", "m", verdict_state=unchecked.state, verified=True
    )

    assert strong.standing == A.Layer.MANIFEST.standing
    assert weak.standing == 0

    # With a checked manifest, the AI watermark is an irreducible contradiction.
    assert (
        A.adjudicate([strong, _watermark("ai")], claim="origin").outcome
        is A.Outcome.CONTRADICTED
    )
    # With an unchecked one, there is nothing of standing to contradict.
    assert (
        A.adjudicate([weak, _watermark("ai")], claim="origin").value == "ai"
    )


def test_nothing_asserts_without_passing_both_gates():
    """The end-to-end invariant: no positive claim escapes either module."""
    cases = [
        V.from_status_codes([], manifest_present=False),
        V.from_status_codes(COMPLETE, ocsp_checked=False),
        V.from_status_codes(["signingCredential.ocsp.revoked"]),
        V.from_status_codes(["assertion.dataHash.mismatch"]),
        V.from_status_codes(["claim.multiple"]),
        V.from_status_codes(["signingCredential.untrusted"]),
    ]
    assert not any(c.is_asserted for c in cases)

    adj = [
        A.adjudicate([], claim="origin"),
        A.adjudicate([_classifier("ai", 1.0)], claim="origin"),
        A.adjudicate([_manifest("human"), _watermark("ai")], claim="origin"),
    ]
    assert not any(a.is_asserted for a in adj)
