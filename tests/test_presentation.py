"""Tests for the accessible presentation contract.

The contract's own invariants run at import time, so importing the module is
itself a test. These tests cover the things an invariant cannot: that each
invariant actually fires when violated, and that the contract composes with the
verdict lattice.

Every test names the accessibility failure it prevents.
"""

import importlib.util
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(path):
    name = path.replace("/", "_").replace(".py", "")
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


V = module("services/adjudicator/verdict.py")
P = module("services/adjudicator/presentation.py")


# =========================================================================
# COVERAGE: the contract must cover the lattice, exactly
# =========================================================================


def test_every_verdict_state_has_a_presentation():
    """A state with no row would be announced by whatever fallback the UI has,
    which is how an unhandled state gets presented as if it were understood."""
    for integrity in V.Integrity:
        assert P.for_state(integrity.name.lower()) is not None
    assert P.for_state("valid_revocation_unknown") is not None


COMPLETE = [
    "claimSignature.validated",
    "signingCredential.trusted",
    "assertion.dataHash.match",
]


def test_a_verdict_object_maps_straight_through():
    v = V.from_status_codes(COMPLETE, ocsp_checked=False)
    pres = P.for_verdict(v)
    assert pres.state == v.state == "valid_revocation_unknown"
    assert pres.asserted == v.is_asserted is False


def test_asserted_flags_agree_between_the_two_modules():
    """If these ever disagreed, the UI would show a pass for a verdict the
    lattice refuses to assert — the exact failure verdict.py exists to stop."""
    cases = [
        V.from_status_codes([], manifest_present=False),
        V.from_status_codes(COMPLETE + ["signingCredential.ocsp.notRevoked"]),
        V.from_status_codes(COMPLETE, ocsp_checked=False),
        V.from_status_codes(["signingCredential.ocsp.revoked"]),
        V.from_status_codes(["assertion.dataHash.mismatch"]),
        V.from_status_codes(["claim.multiple"]),
        V.from_status_codes(["signingCredential.untrusted"]),
        V.from_status_codes(["signingCredential.expired"]),
    ]
    for verdict in cases:
        assert P.for_verdict(verdict).asserted == verdict.is_asserted, verdict.state


def test_exactly_one_state_is_a_positive_assurance():
    assert [p.state for p in P.all_states() if p.asserted] == ["valid"]
    assert [p.state for p in P.all_outcomes() if p.asserted] == ["supported"]


def test_unknown_state_raises_rather_than_falling_back():
    with pytest.raises(KeyError, match="do not fall back to a generic label"):
        P.for_state("some_future_state")


# =========================================================================
# SC 1.4.1 — meaning must survive the loss of colour
# =========================================================================


def test_codes_are_unique_across_both_tables():
    """Both tables render in the same panel, so a shared code is two findings
    wearing the same tile. The conformance harness caught exactly this: "XX"
    was serving both `conflicted` and `contradicted`."""
    codes = [p.code for p in P.all_states()] + [p.code for p in P.all_outcomes()]
    assert len(codes) == len(set(codes)), f"duplicate code(s) in {codes}"


def test_labels_are_unique_across_both_tables():
    labels = [p.label for p in P.all_states()] + [p.label for p in P.all_outcomes()]
    assert len(labels) == len(set(labels))


def test_codes_stay_tile_sized():
    for p in list(P.all_states()) + list(P.all_outcomes()):
        assert 2 <= len(p.code) <= 3, p


def test_every_state_has_a_visible_label_not_just_a_code():
    """A bare two-letter code is an unexplained abbreviation. The label is what
    makes the tile meaningful to someone who has not learned the scheme."""
    for p in P.all_states():
        assert p.label.strip()
        assert p.label != p.code


def test_the_legend_covers_every_state():
    legend = P.legend()
    assert len(legend) == len(P.all_states())
    assert {r["code"] for r in legend} == {p.code for p in P.all_states()}


# =========================================================================
# ANNOUNCEMENT HYGIENE — the screen-reader surface
# =========================================================================


def test_announcements_are_single_complete_sentences():
    """Two badges render as two announcements, which a screen reader reads in
    sequence as two apparently contradictory verdicts with no grammatical
    relationship. One sentence states the finding and its limit together."""
    for p in list(P.all_states()) + list(P.all_outcomes()):
        text = p.announcement
        assert text.endswith("."), p.state
        assert text.count(".") == 1, f"{p.state}: {text.count('.')} sentences"
        assert text[0].isupper(), p.state


def test_no_assurance_language_on_a_state_that_assures_nothing():
    banned = P._ASSURANCE_WORDS
    for p in list(P.all_states()) + list(P.all_outcomes()):
        if p.asserted:
            continue
        words = {w.strip(".,;:()").lower() for w in p.announcement.split()}
        words |= {w.strip(".,;:()").lower() for w in p.name.split()}
        assert not (words & banned), f"{p.state} uses {sorted(words & banned)}"


def test_the_accessible_name_never_tells_less_than_the_visible_label():
    """The lazy implementation sets aria-label to the short label, which gives
    a screen-reader user strictly less than a sighted user is shown."""
    for p in list(P.all_states()) + list(P.all_outcomes()):
        assert p.name.strip().lower() != p.label.strip().lower(), p.state
        assert len(p.name) >= len(p.label), p.state


def test_unknown_check_states_say_the_check_was_not_performed():
    """"Revocation unknown" must read as a fact about our check, not as a
    property of the file. c2pa-rs defines the underlying code as "The validator
    chose not to perform an online OCSP check" — a statement about the
    validator."""
    p = P.for_state("valid_revocation_unknown")
    assert "was not checked" in p.announcement
    assert "would look exactly like" in p.announcement


def test_unsigned_is_announced_as_information_free_in_both_directions():
    text = P.for_state("unsigned").announcement
    assert "neither evidence for it nor evidence against it" in text


def test_revoked_announcement_separates_authority_from_content():
    """Revoked is not tampered. The announcement must not imply the content
    failed its binding — that is the false claim Verifieddit's single red label
    makes, rendering a revoked credential as "altered after signing"."""
    text = P.for_state("revoked").announcement
    assert "may be unchanged" in text
    assert "withdrawn" in text
    assert "binding" not in text


def test_tampered_announcement_does_not_attribute_a_cause():
    """A hash mismatch can be re-encoding, metadata stripping or a CDN
    transform. Saying the content "was changed" asserts an act; saying the
    check failed states the finding."""
    text = P.for_state("tampered").announcement
    assert "does not establish when, why or by whom" in text


def test_unverified_is_distinct_from_both_unsigned_and_valid():
    """Codex's addition: "nothing failed" is not "everything checked"."""
    p = P.for_state("unverified")
    assert p.code == "NV"
    assert p.asserted is False
    # Wording is Codex's; assert the property, not the phrasing.
    assert not p.asserted
    assert any(w in p.announcement.lower() for w in ("missing", "do not establish", "not available"))


# =========================================================================
# THE INVARIANTS THEMSELVES MUST FIRE
# =========================================================================
# An invariant that cannot be shown to fail is decoration. Each test below
# mutates the table, re-runs the checker, and asserts it raises.


def _with_row(table_attr, state, **changes):
    """Context-manager-ish helper: swap one row, run verify_contract, restore."""
    table = getattr(P, table_attr)
    original = table[state]
    table[state] = replace(original, **changes)
    try:
        P.verify_contract()
    finally:
        table[state] = original


def test_duplicate_code_is_rejected():
    with pytest.raises(P.ContractViolation, match="duplicate code"):
        _with_row("_TABLE", "revoked", code="TA")


def test_duplicate_accessible_name_is_rejected():
    with pytest.raises(P.ContractViolation, match="duplicate name"):
        _with_row("_TABLE", "revoked", name=P.for_state("tampered").name)


def test_blank_field_is_rejected():
    with pytest.raises(P.ContractViolation, match="is empty"):
        _with_row("_TABLE", "revoked", label="   ")


def test_oversized_code_is_rejected():
    with pytest.raises(P.ContractViolation, match="2-3"):
        _with_row("_TABLE", "revoked", code="REVOKED")


def test_assurance_language_on_a_non_asserted_state_is_rejected():
    with pytest.raises(P.ContractViolation, match="assurance language"):
        _with_row(
            "_TABLE", "revoked",
            announcement="This content is verified and the signer is not disputed.",
        )


def test_announcement_without_a_limitation_is_rejected():
    with pytest.raises(P.ContractViolation, match="does not state a limitation"):
        _with_row("_TABLE", "revoked", announcement="The credential was revoked.")


def test_multi_sentence_announcement_is_rejected():
    with pytest.raises(P.ContractViolation, match="exactly one"):
        _with_row(
            "_TABLE", "revoked",
            announcement="The credential was revoked. It is not current.",
        )


def test_announcement_without_a_period_is_rejected():
    with pytest.raises(P.ContractViolation, match="sentence-complete"):
        _with_row(
            "_TABLE", "revoked",
            announcement="The credential was revoked but the bytes may be unchanged",
        )


def test_accessible_name_duplicating_the_label_is_rejected():
    with pytest.raises(P.ContractViolation, match="duplicates the visible label"):
        _with_row("_TABLE", "revoked", name="Credential revoked")


def test_accessible_name_shorter_than_the_label_is_rejected():
    with pytest.raises(P.ContractViolation, match="told less than the sighted user"):
        _with_row("_TABLE", "revoked", name="Rvk")


def test_unknown_check_state_losing_its_wording_is_rejected():
    """I7 specifically. The replacement below deliberately satisfies I5 (it
    contains a limitation marker) so that the test reaches I7 rather than
    tripping the earlier invariant — otherwise this test would pass for the
    wrong reason and I7 would be unverified."""
    with pytest.raises(P.ContractViolation, match="must say the check was not performed"):
        _with_row(
            "_TABLE", "valid_revocation_unknown",
            announcement="The revocation status of this credential is not known.",
        )


def test_a_second_asserted_state_is_rejected():
    with pytest.raises(P.ContractViolation, match="exactly one asserted state"):
        _with_row("_TABLE", "revoked", asserted=True)


def test_cross_table_code_collision_is_rejected():
    """The regression for the real defect the harness found."""
    with pytest.raises(P.ContractViolation, match="cross-table duplicate code"):
        _with_row("_OUTCOME_TABLE", "contradicted", code="CF")


def test_the_table_restores_cleanly_after_every_mutation():
    """Guard against a failed test leaving the module poisoned for the rest of
    the suite."""
    P.verify_contract()
    assert P.for_state("revoked").code == "RV"
    assert P.for_state("conflicted").code == "CF"
    assert P.for_outcome("contradicted").code == "XX"


# =========================================================================
# SERIALISATION — the harness consumes this
# =========================================================================


def test_to_dict_is_json_round_trippable():
    import json

    for p in P.all_states():
        d = p.to_dict()
        assert json.loads(json.dumps(d)) == d
        assert d["spec_version"] == P.SPEC_VERSION
        assert set(d) >= {"state", "code", "label", "name", "announcement", "shape", "asserted"}
