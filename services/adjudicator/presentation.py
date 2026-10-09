"""Accessible presentation contract for verdict states.

WHY THIS IS A MODULE AND NOT CSS
--------------------------------
In every reader-side verifier examined, the accessible name and the visible
label are produced in different places — the badge colour in CSS, the tooltip
in one template, the `aria-label` in another. They drift. When they drift, a
screen-reader user and a sighted user are told different things about the same
file, and nobody notices because no test compares them.

So the mapping from a verdict to **all four of its surfaces** lives here, in one
table, with invariants enforced at import time:

    code          the monochrome tile text (rating-label idiom: "OK", "RV")
    label         the always-visible short text next to the tile
    name          the accessible name (what a screen reader announces for the
                  control)
    announcement  the full live-region sentence, complete on its own

`verify_contract()` runs at import and raises if any invariant is broken, so a
drifted string fails the build rather than shipping.

THE DESIGN CONSTRAINT THAT MAKES THIS EASY
------------------------------------------
The house style is monochrome, modelled on film and TV content-rating labels.
That is not a limitation to work around — a two-glyph monochrome tile plus an
always-visible text label satisfies WCAG 2.2 SC 1.4.1 (Use of Color) **by
construction**: there is no colour carrying information, so there is nothing to
remediate. It also survives Windows High Contrast, grayscale printing, and
the 1-bit rendering some e-readers use.

THE PART NOBODY ELSE DOES
-------------------------
Announcing *uncertainty* coherently. A state like "valid signature, revocation
never checked" is two facts, and the obvious implementation renders two badges.
A screen reader then reads them in sequence as two apparently contradictory
verdicts — "valid", then "unknown" — with no grammatical relationship. The user
has to reconstruct the logic. So `announcement` is always **one
sentence-complete string** that states the finding and its limitation together,
and invariant I6 enforces that.

Depends only on verdict.py and the stdlib.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, replace
from pathlib import Path

SPEC_VERSION = "presentation/1.1.0"


def _sibling(name: str):
    """Import a sibling module by path, with sys.modules registration."""
    mod_name = f"_adjudicator_{name}"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(
        mod_name, Path(__file__).with_name(f"{name}.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


_v = _sibling("verdict")
Integrity = _v.Integrity
Revocation = _v.Revocation


@dataclass(frozen=True)
class Presentation:
    """Everything the UI needs for one state, from one place."""

    state: str
    #: Monochrome tile text. Two or three characters; no colour dependency.
    code: str
    #: Always-visible short label. Never hidden — the code alone would be an
    #: unexplained abbreviation, which fails users who have not learned it.
    label: str
    #: Accessible name for the control. Must stand alone and must not assert
    #: more than the verdict supports.
    name: str
    #: The complete live-region sentence. One sentence-complete string.
    announcement: str
    #: Non-colour visual treatment, applied as a data attribute so CSS carries
    #: no semantics of its own.
    shape: str
    #: True only where the state is a positive assurance.
    asserted: bool

    def to_dict(self) -> dict:
        return {
            "spec_version": SPEC_VERSION,
            "state": self.state,
            "code": self.code,
            "label": self.label,
            "name": self.name,
            "announcement": self.announcement,
            "shape": self.shape,
            "asserted": self.asserted,
        }


# --- The table ------------------------------------------------------------
# One row per state string produced by verdict.Verdict.state. The shapes are
# deliberately distinguishable by outline treatment alone, so the tiles remain
# distinct in grayscale, in forced-colors mode, and at 1-bit depth.

_TABLE: dict[str, Presentation] = {
    "unsigned": Presentation(
        state="unsigned",
        code="NC",
        label="No credential",
        name="No provenance credential found",
        announcement=(
            "No provenance credential was found for this content, which is "
            "neither evidence for it nor evidence against it, because most "
            "content carries no credential at all."
        ),
        shape="dashed",
        asserted=False,
    ),
    "unverified": Presentation(
        state="unverified",
        code="NV",
        label="Verification incomplete",
        name="Verification incomplete: signature, signer or content binding not established",
        announcement=(
            "The supplied results do not establish complete checking of the "
            "signature, the signer and the content binding together, so there "
            "is no positive finding to report."
        ),
        shape="solid",
        asserted=False,
    ),
    "unverified": Presentation(
        state="unverified", code="NV", label="Verification incomplete",
        name="Required credential verification is incomplete",
        announcement="The supplied results do not establish complete signature, trust and content-binding checks, so positive assurance is not available.",
        shape="dashed", asserted=False,
    ),
    "valid": Presentation(
        state="valid",
        code="OK",
        label="Credential checked",
        name="Provenance credential checked, including revocation",
        announcement=(
            "A provenance credential is present, the content matches what was "
            "signed, the signer is on the trust list in use, and revocation was "
            "checked and is current."
        ),
        shape="double",
        asserted=True,
    ),
    "valid_revocation_unknown": Presentation(
        state="valid_revocation_unknown",
        code="OK?",
        label="Checked except revocation",
        name="Credential intact, but revocation was not checked",
        announcement=(
            "The content matches what was signed and the signer is on the trust "
            "list in use, but revocation was not checked, so a credential that "
            "has been withdrawn would look exactly like a current one here."
        ),
        shape="double-dotted",
        asserted=False,
    ),
    "unrecognized_signer": Presentation(
        state="unrecognized_signer",
        code="UR",
        label="Signer unrecognised",
        name="Reported signer not on the trust list in use",
        announcement=(
            "The results report a signer that is not on the trust list in use, "
            "which indicates only that this tool was not configured to "
            "recognise them and says nothing about their honesty."
        ),
        shape="solid",
        asserted=False,
    ),
    "expired": Presentation(
        state="expired",
        code="EX",
        label="Certificate expired",
        name="Signing certificate validity issue reported",
        announcement=(
            "The results report that the signing certificate was outside its "
            "validity period with no trusted timestamp present, which is common "
            "and often harmless."
        ),
        shape="solid",
        asserted=False,
    ),
    "conflicted": Presentation(
        state="conflicted",
        code="CF",
        label="Claims disagree",
        name="Provenance claims disagree; none is authoritative",
        announcement=(
            "Two or more provenance claims of equal standing disagree about "
            "this content, and because no rule resolves which one is "
            "authoritative, none of them is presented as the answer."
        ),
        shape="heavy",
        asserted=False,
    ),
    "revoked": Presentation(
        state="revoked",
        code="RV",
        label="Credential revoked",
        name="Signing credential revoked by its issuer",
        announcement=(
            "The credential that signed this content was revoked by its issuer, "
            "so although the content itself may be unchanged, the authority to "
            "vouch for it has been withdrawn."
        ),
        shape="heavy-struck",
        asserted=False,
    ),
    "tampered": Presentation(
        state="tampered",
        code="TA",
        label="Binding or signature failed",
        name="Content binding or signature verification failed",
        announcement=(
            "The content binding or signature check failed, which means the "
            "content is not what was signed, but it does not establish when, "
            "why or by whom it differs."
        ),
        shape="heavy-slashed",
        asserted=False,
    ),
}

#: Adjudication outcomes get their own row set, same contract.
_OUTCOME_TABLE: dict[str, Presentation] = {
    "supported": Presentation(
        state="supported",
        code="SU",
        label="Supported",
        name="Claim supported by evidence that carries standing",
        announcement=(
            "This claim is supported by provenance evidence that carries "
            "standing under the published adjudication rules."
        ),
        shape="double",
        asserted=True,
    ),
    "unsupported": Presentation(
        state="unsupported",
        code="NS",
        label="Not established",
        name="Claim not established by the available evidence",
        announcement=(
            "This claim is not established, because the available signals do "
            "not carry enough standing to support it, and the absence of a "
            "signal is not evidence of the opposite."
        ),
        shape="dashed",
        asserted=False,
    ),
    "contradicted": Presentation(
        state="contradicted",
        code="XX",
        label="Evidence contradicts",
        name="Evidence of equal standing contradicts itself",
        announcement=(
            "Signals of equal standing disagree about this claim, and because "
            "no rule resolves which one is authoritative, none of them is "
            "presented as the answer."
        ),
        shape="heavy",
        asserted=False,
    ),
}


# --- Invariants -----------------------------------------------------------

#: Words that assert assurance. Permitted only on an asserted state.
#:
#: This check is deliberately naive — plain word matching, no negation
#: handling. A smarter check is a check that can be argued past, and the whole
#: value of the invariant is that it cannot be. The cost is that a legitimate
#: negated use ("not genuine") also trips it, which is fine: the fix is to
#: write the sentence without the loaded word, and the result is clearer copy
#: anyway. This exact trip happened while writing the `unsigned` row.
_ASSURANCE_WORDS = frozenset(
    {
        "authentic",
        "authenticated",
        "genuine",
        "safe",
        "trustworthy",
        "verified",
        "guaranteed",
        "proven",
        "certified",
        "legitimate",
    }
)

#: A non-asserted announcement must carry one of these, so that no state
#: without standing is announced as a bare finding.
_LIMITATION_MARKERS = (
    "not ",
    "but ",
    "neither ",
    "says nothing",
    "would look",
    "no rule",
    "may be unchanged",
    "often harmless",
)


class ContractViolation(AssertionError):
    """Raised when the presentation table breaks one of its own invariants."""


def verify_contract() -> None:
    """Enforce every invariant. Called at import; raises on violation.

    The invariants are the point of the module. A table that can drift is a
    table that will drift, and the drift is invisible to users who only
    experience one of the two surfaces.
    """
    for table_name, table in (("verdict", _TABLE), ("outcome", _OUTCOME_TABLE)):
        rows = list(table.values())

        # I0 — the key must match the row's own state.
        for key, row in table.items():
            if key != row.state:
                raise ContractViolation(
                    f"{table_name}: key {key!r} does not match row state {row.state!r}"
                )

        # I1 — codes unique within a table. Two states sharing a tile glyph
        # would be indistinguishable to a sighted user in monochrome.
        for field in ("code", "label", "name"):
            seen: dict[str, str] = {}
            for row in rows:
                value = getattr(row, field)
                if value in seen:
                    raise ContractViolation(
                        f"{table_name}: duplicate {field} {value!r} on states "
                        f"{seen[value]!r} and {row.state!r} — states must be "
                        "distinguishable on every surface independently"
                    )
                seen[value] = row.state

        for row in rows:
            # I2 — nothing may be blank. A blank accessible name is announced
            # as the element's tag or its raw code.
            for field in ("code", "label", "name", "announcement", "shape"):
                if not getattr(row, field).strip():
                    raise ContractViolation(
                        f"{table_name}/{row.state}: {field} is empty"
                    )

            # I3 — the code is shorthand and must stay short enough to be a
            # tile rather than a sentence.
            if not 2 <= len(row.code) <= 3:
                raise ContractViolation(
                    f"{table_name}/{row.state}: code {row.code!r} must be 2-3 "
                    "characters to read as a rating-label tile"
                )

            # I4 — no unqualified assurance language on a state that carries no
            # assurance. This is the invariant that stops copy drifting into
                # "verified" on a state that verified nothing.
            words = {
                w.strip(".,;:()").lower() for w in row.announcement.split()
            } | {w.strip(".,;:()").lower() for w in row.name.split()}
            offending = words & _ASSURANCE_WORDS
            if offending and not row.asserted:
                raise ContractViolation(
                    f"{table_name}/{row.state}: non-asserted state uses "
                    f"assurance language {sorted(offending)!r}"
                )

            # I5 — a non-asserted announcement must state its limitation.
            if not row.asserted:
                if not any(m in row.announcement.lower() for m in _LIMITATION_MARKERS):
                    raise ContractViolation(
                        f"{table_name}/{row.state}: non-asserted announcement "
                        "does not state a limitation"
                    )

            # I6 — one sentence-complete string. Enforced because the failure
            # mode is a screen reader reading two badges as two contradictory
            # verdicts with no grammatical relationship between them.
            text = row.announcement.strip()
            if not text.endswith("."):
                raise ContractViolation(
                    f"{table_name}/{row.state}: announcement must be "
                    "sentence-complete and end with a period"
                )
            if text.count(".") != 1:
                raise ContractViolation(
                    f"{table_name}/{row.state}: announcement must be exactly one "
                    f"sentence; found {text.count('.')} periods"
                )
            if not text[0].isupper():
                raise ContractViolation(
                    f"{table_name}/{row.state}: announcement must start with a "
                    "capital letter"
                )

            # I7 — where the uncertainty is about *our check* rather than about
            # the content, the sentence must say so. Otherwise a user reads
            # "unknown" as a property of the file.
            if "revocation_unknown" in row.state:
                if "was not checked" not in row.announcement:
                    raise ContractViolation(
                        f"{table_name}/{row.state}: an unknown-check state must "
                        "say the check was not performed, not merely that "
                        "something is unknown"
                    )

            # I8 — the accessible name must not be a truncation of the label,
            # which is the common lazy implementation and tells a screen-reader
            # user strictly less than a sighted user is shown.
            if row.name.strip().lower() == row.label.strip().lower():
                raise ContractViolation(
                    f"{table_name}/{row.state}: accessible name duplicates the "
                    "visible label and adds nothing"
                )
            if len(row.name) < len(row.label):
                raise ContractViolation(
                    f"{table_name}/{row.state}: accessible name is shorter than "
                    "the visible label — the screen-reader user would be told "
                    "less than the sighted user"
                )

    # I11 — codes and labels must be unique ACROSS tables, not only within
    # one. The two tables render in the same panel, so a code reused between
    # them is two different findings wearing the same tile. This invariant was
    # added after the conformance harness caught exactly that: "XX" was serving
    # both the verdict state `conflicted` and the adjudication outcome
    # `contradicted`.
    cross: dict[str, str] = {}
    for table_name, table in (("verdict", _TABLE), ("outcome", _OUTCOME_TABLE)):
        for row in table.values():
            for field in ("code", "label"):
                value = getattr(row, field)
                key = f"{field}:{value}"
                if key in cross:
                    raise ContractViolation(
                        f"cross-table duplicate {field} {value!r}: "
                        f"{cross[key]} and {table_name}/{row.state}. Both tables "
                        "render in the same panel, so the two findings would be "
                        "indistinguishable."
                    )
                cross[key] = f"{table_name}/{row.state}"

    # I9 — the verdict table must cover every state verdict.py can emit.
    expected = {i.name.lower() for i in Integrity} | {"valid_revocation_unknown"}
    missing = expected - set(_TABLE)
    if missing:
        raise ContractViolation(
            f"verdict: no presentation for state(s) {sorted(missing)!r} — every "
            "state the lattice can produce must have one"
        )
    extra = set(_TABLE) - expected
    if extra:
        raise ContractViolation(
            f"verdict: presentation for unreachable state(s) {sorted(extra)!r}"
        )

    # I10 — exactly one asserted state per table. More than one positive
    # assurance state is a sign the lattice has grown an unreviewed pass.
    for table_name, table in (("verdict", _TABLE), ("outcome", _OUTCOME_TABLE)):
        asserted = [r.state for r in table.values() if r.asserted]
        if len(asserted) != 1:
            raise ContractViolation(
                f"{table_name}: expected exactly one asserted state, found "
                f"{asserted!r}"
            )


verify_contract()


# --- Public API -----------------------------------------------------------


def for_state(state: str) -> Presentation:
    """Presentation for a `Verdict.state` string."""
    try:
        return _TABLE[state]
    except KeyError:
        raise KeyError(
            f"No presentation for verdict state {state!r}. Add a row to _TABLE; "
            "do not fall back to a generic label, because a generic label is "
            "how an unhandled state gets announced as if it were understood."
        ) from None


def for_outcome(outcome: str) -> Presentation:
    """Presentation for an `Adjudication.outcome` value."""
    try:
        return _OUTCOME_TABLE[outcome]
    except KeyError:
        raise KeyError(f"No presentation for adjudication outcome {outcome!r}") from None


def for_verdict(verdict) -> Presentation:
    """Presentation for a `verdict.Verdict` instance."""
    row = for_state(verdict.state)
    if row.asserted != verdict.is_asserted:
        raise ContractViolation("Presentation cannot assert more than its supplied verdict")
    if verdict.state == "valid_revocation_unknown" and verdict.revocation.value == "unknown_inaccessible":
        return replace(row, name="Credential intact, but revocation could not be established",
                       announcement="Content binding and signer checks succeeded, but revocation could not be established, so a withdrawn credential could appear current here.")
    return row


def all_states() -> tuple[Presentation, ...]:
    """Every verdict presentation, in severity order. Used by the legend and
    by the conformance harness, which renders all of them and checks that they
    stay distinguishable."""
    order = [i.name.lower() for i in Integrity]
    order.insert(order.index("valid") + 1, "valid_revocation_unknown")
    return tuple(_TABLE[s] for s in order)


def all_outcomes() -> tuple[Presentation, ...]:
    return tuple(_OUTCOME_TABLE[k] for k in ("supported", "unsupported", "contradicted"))


def legend() -> list[dict]:
    """The legend rows. A two-letter code is meaningless without one, and
    shipping the code without the legend would make the tile an unexplained
    abbreviation (WCAG 3.1.3 / 3.1.4 territory)."""
    return [
        {"code": p.code, "label": p.label, "meaning": p.name}
        for p in all_states()
    ]
