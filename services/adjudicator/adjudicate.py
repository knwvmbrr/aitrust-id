"""Experimental per-claim precedence policy over supplied observations.

No watermark, manifest or file is read here. Explicit upstream verification is
required for strong standing; flags are trusted adapter inputs, not evidence
themselves. Equal manifest/watermark standing is a proposal requiring acceptance.
See docs/adjudication-spec.md and docs/competitive-differentiation.md."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence

SPEC_VERSION = "adjudication/1.0.1"


class Layer(Enum):
    """Evidentiary layer a signal comes from, with its standing.

    `standing` is the rank used by the precedence rules. Equal standing means a
    disagreement is irreducible and must be reported as such.
    """

    #: A signed C2PA/COSE assertion. Cryptographically bound to a credential.
    MANIFEST = ("manifest", 3)

    #: A durable soft binding read out of the content itself (TrustMark, ISCC,
    #: SynthID-class markers). Intentionally embedded and robust, but carries no
    #: signature of its own. Equal standing to MANIFEST *by design* -- that
    #: equality is what makes the authenticated-fake case irreducible.
    WATERMARK = ("watermark", 3)

    #: Unsigned file metadata: EXIF, IPTC, XMP, HTTP headers. Trivially
    #: editable by anyone who touches the file.
    METADATA = ("metadata", 1)

    #: A statistical classifier. A surrogate for the thing we want to know, and
    #: never a reader of an intentional signal.
    CLASSIFIER = ("classifier", 0)

    def __init__(self, label: str, standing: int) -> None:
        self.label = label
        self.standing = standing


class Outcome(Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"


#: Two distinct thresholds, because "may support a claim alone" and "may argue
#: with a claim" are different powers and conflating them loses information.
#:
#: ASSERT_FLOOR -- a signal at or above this may, on its own, support a claim.
#: Unsigned metadata cannot (anyone who touches the file can write it) and a
#: classifier cannot (it is a surrogate).
ASSERT_FLOOR = 2

#: CONTEST_FLOOR -- a signal at or above this enters the disagreement
#: comparison and is recorded when overruled. Unsigned metadata does enter:
#: EXIF that contradicts a signed manifest is worth showing a user even though
#: it settles nothing. A classifier does not enter at all, so it can never
#: contradict an intentional signal.
CONTEST_FLOOR = 1


@dataclass(frozen=True)
class Signal:
    """One piece of evidence about one property of one asset.

    Args:
      layer: where it came from.
      claim: the property asserted, e.g. "origin". Signals are only ever
        compared within the same claim.
      value: the asserted value, e.g. "human" / "ai" / "ai_assisted".
      source: free-text provenance of the signal itself, for the audit record.
        Required: an unattributable signal is not evidence.
      confidence: 0..1. Only meaningful for CLASSIFIER; ignored for precedence.
      verdict_state: for MANIFEST signals, the `Verdict.state` from
        verdict.py. A manifest whose own verdict is not assertable forfeits
        standing -- a revoked or tampered manifest does not get to win an
        argument.
    """

    layer: Layer
    claim: str
    value: str
    source: str
    confidence: float | None = None
    verdict_state: str | None = None
    #: Whether the signal's own integrity was established. REQUIRED for
    #: MANIFEST and WATERMARK (see __post_init__); meaningless for METADATA and
    #: CLASSIFIER, which carry no integrity of their own.
    #:
    #: What it means per layer, because an undocumented boolean is a flag a
    #: caller will guess at:
    #:   MANIFEST  -- the manifest validated, and `verdict_state` carries the
    #:                result. verified=True with a verdict_state other than
    #:                "valid" still forfeits standing.
    #:   WATERMARK -- the soft binding was DECODED and RESOLVED against a
    #:                manifest repository, and that manifest validated. A bare
    #:                watermark hit is NOT verified: a decoded payload is a
    #:                pointer, not an assertion, and perceptual-hash collisions
    #:                are a documented attack (NeuralHash: 90.81% forced-
    #:                collision success, Struppek et al., FAccT 2022).
    #:
    #: Left as None rather than defaulting to False on purpose -- see below.
    verified: bool | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.layer, Layer):
            raise ValueError("Signal requires a known layer")
        # `verified` is REQUIRED for the two layers that can assert, and has no
        # default. Corrected 2026-10-09: it previously defaulted to False,
        # which meant every caller that did not know about the field silently
        # lost standing and every claim fell through to R5 UNSUPPORTED with no
        # indication why. A silently inert adjudicator is worse than a loud
        # one, because the obvious "fix" a developer reaches for is to set
        # verified=True everywhere, which defeats the gate entirely. Making it
        # required keeps the fail-safe intent and makes the omission visible.
        if self.layer in (Layer.MANIFEST, Layer.WATERMARK):
            if self.verified is None:
                raise ValueError(
                    f"{self.layer.label} signals must state `verified` "
                    "explicitly. True means the manifest validated, or the soft "
                    "binding was decoded AND resolved to a manifest that "
                    "validated. If you do not know, pass verified=False — but "
                    "pass it, so the omission is a decision rather than a "
                    "default."
                )
            if not isinstance(self.verified, bool):
                raise ValueError("Signal.verified must be a bool when stated")
            if self.layer is Layer.WATERMARK and self.verified and not self.source:
                raise ValueError(
                    "A verified WATERMARK signal must name the resolver in "
                    "`source`; otherwise verified=True is unfalsifiable."
                )
        elif self.verified is not None:
            raise ValueError(
                f"`verified` is meaningless for {self.layer.label} signals, "
                "which carry no integrity of their own. Leave it unset."
            )
        if not all(isinstance(v, str) and v.strip() for v in (self.claim, self.value, self.source)):
            raise ValueError("Signal claim, value and source are required: empty inputs are not evidence")
        if not self.source:
            raise ValueError(
                "Signal.source is required: an unattributable signal is not "
                "evidence and must not enter adjudication."
            )
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0,1], got {self.confidence}")
        if self.layer is Layer.CLASSIFIER and self.confidence is None:
            raise ValueError(
                "A CLASSIFIER signal must carry a confidence. An unquantified "
                "classifier output is not reportable."
            )

    @property
    def standing(self) -> int:
        """Effective standing, after forfeiture.

        A MANIFEST signal only carries its layer standing if the manifest
        itself validated to an assertable state. This is the join between this
        module and verdict.py, and it is the reason an authenticated fake whose
        signature was *also* revoked collapses to a simple REVOKED answer
        rather than a contradiction.
        """
        if self.layer in (Layer.MANIFEST, Layer.WATERMARK) and not self.verified:
            return 0  # unverified assertion-capable signal: no standing
        if self.layer is Layer.MANIFEST and self.verdict_state != "valid":
            return 0
        return self.layer.standing

    @property
    def may_assert(self) -> bool:
        return self.standing >= ASSERT_FLOOR

    @property
    def may_contest(self) -> bool:
        return self.standing >= CONTEST_FLOOR


@dataclass(frozen=True)
class Adjudication:
    claim: str
    outcome: Outcome
    value: str | None
    rule: str
    signals: tuple[Signal, ...]
    #: Populated only for CONTRADICTED: the disagreeing values and who said so.
    contradiction: tuple[tuple[str, tuple[str, ...]], ...] = ()
    #: Populated for R4: signals that contested and lost. Kept in the record so
    #: that "the EXIF disagreed" is visible rather than discarded.
    overruled: tuple[Signal, ...] = ()

    @property
    def is_asserted(self) -> bool:
        return self.outcome is Outcome.SUPPORTED

    def render(self) -> str:
        if self.outcome is Outcome.SUPPORTED:
            return f"{self.claim}: {self.value}."
        if self.outcome is Outcome.UNSUPPORTED:
            return (
                f"{self.claim}: not established. The available signals do not "
                "carry enough standing to support a claim, and absence of a "
                "signal is not evidence of the opposite."
            )
        pairs = "; ".join(
            f"{value!r} per {', '.join(srcs)}" for value, srcs in self.contradiction
        )
        return (
            f"{self.claim}: CONTRADICTED. Signals of equal standing disagree — "
            f"{pairs}. No rule resolves which is authoritative, so none is "
            "presented as the answer."
        )

    def to_dict(self) -> dict:
        return {
            "spec_version": SPEC_VERSION,
            "claim": self.claim,
            "outcome": self.outcome.value,
            "value": self.value,
            "rule": self.rule,
            "asserted": self.is_asserted,
            "contradiction": [
                {"value": v, "sources": list(s)} for v, s in self.contradiction
            ],
            "overruled": [
                {"layer": s.layer.label, "value": s.value, "source": s.source}
                for s in self.overruled
            ],
            "signals": [
                {
                    "layer": s.layer.label,
                    "value": s.value,
                    "source": s.source,
                    "confidence": s.confidence,
                    "standing": s.standing,
                    "verdict_state": s.verdict_state,
                    "verified": s.verified,
                }
                for s in self.signals
            ],
            "message": self.render(),
        }


# --- The rules, in order -------------------------------------------------
# Each returns an Adjudication or None. The first that fires wins. They are
# numbered so that a published rule can be cited and contested by number.

RULES_DOC = """
R1  No signals for a claim -> UNSUPPORTED. Absence is never evidence of the
    negative. (Directly contra the inference pattern that a missing watermark
    means "not AI" -- see Google's own Gemini help copy, which states that if a
    watermark "isn't detected, it means the image or video wasn't created or
    edited by Google AI", while Google's own SynthID portal says only that it
    "is unlikely that this media was made with AI from a SynthID partner".)

R5  No signal reaches ASSERT_FLOOR -> UNSUPPORTED, whatever the classifier
    confidence, and whatever the unsigned metadata says. A surrogate never
    establishes a claim on its own, and a classifier never enters the
    disagreement comparison at all; see the measured FPR asymmetries in Liang
    et al. (arXiv:2304.02819, 61.22% FPR on TOEFL essays vs near-perfect
    accuracy on US 8th-grade essays) and Khvatskii et al. (arXiv:2608.11256,
    25.3% vs 5.6% non-STEM/STEM paper-level flag rates, permutation
    p = 0.0002). A tool that let a classifier overrule a signed assertion
    would inherit those error rates as authority.

R2  All signals at or above CONTEST_FLOOR agree -> SUPPORTED with that value.

R3  Signals at or above CONTEST_FLOOR disagree, and the highest standing among
    them is SHARED -> CONTRADICTED, naming every disagreeing value and its
    sources. This is the authenticated-fake case: a manifest and a watermark
    have equal standing by design, so their disagreement is irreducible and we
    do not pick a winner.

R4  Signals at or above CONTEST_FLOOR disagree but one strictly outranks the
    rest -> SUPPORTED with the higher-standing value, and the losing signals
    are recorded in `overruled` rather than discarded. (Reached when a signed
    manifest outranks unsigned EXIF.)

Manifest/watermark standing requires explicit upstream verification; manifests
also require a valid verdict. This module does not verify files or signatures.
Rule order is R1, R5, then R2/R3/R4 by comparison. R5 precedes the comparison
rules so that a set containing only non-asserting signals can never produce a
value, however much those signals agree with each other.
"""


def adjudicate(signals: Iterable[Signal], *, claim: str) -> Adjudication:
    """Adjudicate one claim from a set of signals.

    Signals for other claims are ignored, so the caller may pass everything it
    has.
    """
    relevant = tuple(s for s in signals if s.claim == claim)

    if not relevant:
        return Adjudication(claim, Outcome.UNSUPPORTED, None, "R1", relevant)

    # R5 before any comparison: without a signal that may assert, no amount of
    # agreement among weaker signals produces a value.
    if not any(s.may_assert for s in relevant):
        return Adjudication(claim, Outcome.UNSUPPORTED, None, "R5", relevant)

    contesting = tuple(s for s in relevant if s.may_contest)
    values = {s.value for s in contesting}
    if len(values) == 1:
        return Adjudication(
            claim, Outcome.SUPPORTED, next(iter(values)), "R2", relevant
        )

    top = max(s.standing for s in contesting)
    top_signals = tuple(s for s in contesting if s.standing == top)
    top_values = {s.value for s in top_signals}

    if len(top_values) > 1:
        grouped: dict[str, list[str]] = {}
        for s in top_signals:
            grouped.setdefault(s.value, []).append(s.source)
        contradiction = tuple(
            (v, tuple(sorted(srcs))) for v, srcs in sorted(grouped.items())
        )
        return Adjudication(
            claim, Outcome.CONTRADICTED, None, "R3", relevant, contradiction
        )

    return Adjudication(
        claim,
        Outcome.SUPPORTED,
        next(iter(top_values)),
        "R4",
        relevant,
        overruled=tuple(s for s in contesting if s.standing < top),
    )


def adjudicate_all(signals: Sequence[Signal]) -> dict[str, Adjudication]:
    """Adjudicate every claim present in `signals`, keyed by claim."""
    return {c: adjudicate(signals, claim=c) for c in sorted({s.claim for s in signals})}
