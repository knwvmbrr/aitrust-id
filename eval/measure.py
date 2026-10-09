"""Statistics over supplied observations, not a platform collection harness.

Wilson intervals, conditional disagreement/accuracy with answer coverage, and
manifest/soft-binding survival summaries. No competitor or platform observations
are obtained by this module. See docs/competitive-differentiation.md."""

from __future__ import annotations

import math
from statistics import NormalDist
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping, Sequence

SPEC_VERSION = "measure/1.0.0"

#: Two-sided critical values, so the common cases need no erf inversion.
_Z = {0.80: 1.2815515655446004, 0.90: 1.6448536269514722, 0.95: 1.959963984540054,
      0.98: 2.3263478740408408, 0.99: 2.5758293035489004}


def z_for(confidence: float) -> float:
    """Two-sided normal critical value for `confidence`.

    Uses an exact table for common levels and the stdlib NormalDist inverse
    normal CDF otherwise.
    """
    if confidence in _Z:
        return _Z[confidence]
    if not 0.0 < confidence < 1.0:
        raise ValueError(f"confidence must be in (0,1), got {confidence}")
    p = 1.0 - (1.0 - confidence) / 2.0
    return NormalDist().inv_cdf(p)


@dataclass(frozen=True)
class Interval:
    """A proportion with a confidence interval and the counts behind it."""

    successes: int
    trials: int
    point: float
    low: float
    high: float
    confidence: float
    method: str = "wilson"

    @property
    def width(self) -> float:
        return self.high - self.low

    def __str__(self) -> str:
        return (
            f"{self.point:.1%} [{self.low:.1%}, {self.high:.1%}] "
            f"({self.successes}/{self.trials}, {self.confidence:.0%} {self.method})"
        )

    def to_dict(self) -> dict:
        return {
            "successes": self.successes,
            "trials": self.trials,
            "point": self.point,
            "low": self.low,
            "high": self.high,
            "confidence": self.confidence,
            "method": self.method,
            "width": self.width,
        }


def wilson(successes: int, trials: int, confidence: float = 0.95) -> Interval:
    """Wilson score interval for a binomial proportion.

    Unlike the normal approximation this never produces a zero-width interval
    and never leaves [0,1], so k=0 and k=n report honestly.

    >>> str(wilson(0, 10))
    '0.0% [0.0%, 27.8%] (0/10, 95% wilson)'
    >>> str(wilson(10, 10))
    '100.0% [72.2%, 100.0%] (10/10, 95% wilson)'
    """
    if type(successes) is not int or type(trials) is not int:
        raise ValueError("successes and trials must be integer counts")
    if trials <= 0:
        raise ValueError("trials must be positive — there is no interval for n=0")
    if not 0 <= successes <= trials:
        raise ValueError(f"successes must be in [0, {trials}], got {successes}")

    z = z_for(confidence)
    n = float(trials)
    p = successes / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    margin = (z / denom) * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))
    low = max(0.0, centre - margin)
    high = min(1.0, centre + margin)
    # Wilson's bounds at the extremes are exactly 0 and 1; floating-point dust
    # otherwise leaves 2.8e-17 and 0.9999999999999999, which break invariant
    # checks downstream for no mathematical reason.
    if successes == 0:
        low = 0.0
    if successes == trials:
        high = 1.0
    return Interval(
        successes=successes,
        trials=trials,
        point=p,
        low=low,
        high=high,
        confidence=confidence,
    )


def min_trials_for_width(target_width: float, *, p: float = 0.5,
                         confidence: float = 0.95, cap: int = 100_000) -> int:
    """Smallest n whose Wilson interval is no wider than `target_width` at `p`.

    Answers the only question that matters before running a survival study:
    how many uploads do I need per platform? Worst case is p=0.5.
    """
    if not 0.0 <= p <= 1.0 or not math.isfinite(p):
        raise ValueError("p must be finite and in [0,1]")
    if type(cap) is not int or cap < 1:
        raise ValueError("cap must be a positive integer")
    if not 0.0 < target_width < 1.0:
        raise ValueError("target_width must be in (0,1)")
    for n in range(1, cap + 1):
        k = int(round(p * n))
        if wilson(k, n, confidence).width <= target_width:
            return n
    raise ValueError(f"no n <= {cap} achieves width {target_width}")


# --- Disagreement measurement -------------------------------------------


class Disagreement(Enum):
    UNANIMOUS = "unanimous"
    SPLIT = "split"
    #: At least one validator produced no answer at all.
    INCOMPLETE = "incomplete"


@dataclass(frozen=True)
class FixtureResult:
    """What every validator said about one fixture."""

    fixture: str
    #: validator name -> state string (e.g. from verdict.Verdict.state), or
    #: None where the validator errored or returned nothing.
    states: Mapping[str, str | None]
    #: The state the fixture is constructed to elicit, when known. Fixtures
    #: with an expected state measure *correctness*; those without measure only
    #: *agreement*, which is a weaker and separately reportable thing.
    expected: str | None = None

    def __post_init__(self) -> None:
        if not self.fixture or not self.states:
            raise ValueError("A fixture and at least one validator are required")
        if any(not isinstance(k, str) or not k or (v is not None and (not isinstance(v, str) or not v))
               for k, v in self.states.items()):
            raise ValueError("Validator names and answers must be nonempty strings, or None for missing answers")

    @property
    def answered(self) -> dict[str, str]:
        return {k: v for k, v in self.states.items() if v is not None}

    @property
    def classification(self) -> Disagreement:
        if len(self.answered) < len(self.states):
            return Disagreement.INCOMPLETE
        return (
            Disagreement.UNANIMOUS
            if len(set(self.answered.values())) <= 1
            else Disagreement.SPLIT
        )

    @property
    def correct(self) -> dict[str, bool] | None:
        if self.expected is None:
            return None
        return {k: v == self.expected for k, v in self.answered.items()}


def disagreement_matrix(
    results: Sequence[FixtureResult],
) -> dict[tuple[str, str], Interval]:
    """Pairwise disagreement rate between every pair of validators.

    Only fixtures where *both* validators of a pair answered are counted, so a
    validator that crashes often does not get a flattering disagreement rate.
    The count is reported in the interval, so that attrition is visible.
    """
    names = sorted({n for r in results for n in r.states})
    out: dict[tuple[str, str], Interval] = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            both = [r for r in results if r.states.get(a) and r.states.get(b)]
            if not both:
                continue
            differ = sum(1 for r in both if r.states[a] != r.states[b])
            out[(a, b)] = wilson(differ, len(both))
    return out


def per_validator_accuracy(
    results: Sequence[FixtureResult],
) -> dict[str, Interval]:
    """Accuracy per validator, over fixtures that declare an expected state."""
    graded = [r for r in results if r.expected is not None]
    names = sorted({n for r in graded for n in r.states})
    out: dict[str, Interval] = {}
    for name in names:
        answered = [r for r in graded if r.states.get(name) is not None]
        if not answered:
            continue
        hits = sum(1 for r in answered if r.states[name] == r.expected)
        out[name] = wilson(hits, len(answered))
    return out


def summarize(results: Sequence[FixtureResult]) -> dict:
    """A full, publishable report. Shaped so that it diffs cleanly in git."""
    counts = {d: 0 for d in Disagreement}
    for r in results:
        counts[r.classification] += 1
    total = len(results)
    return {
        "spec_version": SPEC_VERSION,
        "fixtures": total,
        "graded_fixtures": sum(1 for r in results if r.expected is not None),
        "validators": sorted({n for r in results for n in r.states}),
        "classification_counts": {d.value: c for d, c in counts.items()},
        "answer_coverage": {
            name: {"attempted": sum(name in r.states for r in results),
                   "answered": sum(r.states.get(name) is not None for r in results if name in r.states),
                   "missing": sum(r.states.get(name) is None for r in results if name in r.states)}
            for name in sorted({n for r in results for n in r.states})
        },
        "split_rate": (
            wilson(counts[Disagreement.SPLIT], total).to_dict() if total else None
        ),
        "pairwise_disagreement": {
            f"{a}|{b}": iv.to_dict()
            for (a, b), iv in sorted(disagreement_matrix(results).items())
        },
        "per_validator_accuracy": {
            k: v.to_dict() for k, v in sorted(per_validator_accuracy(results).items())
        },
    }


# --- Survival measurement ------------------------------------------------


@dataclass(frozen=True)
class SurvivalTrial:
    """One fixture through one platform, one time."""

    platform: str
    fixture: str
    #: Did the manifest still validate after the round trip?
    manifest_survived: bool
    #: Did the soft binding (watermark/fingerprint) still resolve?
    soft_binding_survived: bool | None = None
    #: Bytes before/after, for an honest note on re-encoding.
    bytes_in: int | None = None
    bytes_out: int | None = None

    def __post_init__(self) -> None:
        if not self.platform or not self.fixture:
            raise ValueError("Platform and fixture identity are required")
        if type(self.manifest_survived) is not bool or (self.soft_binding_survived is not None and type(self.soft_binding_survived) is not bool):
            raise ValueError("Survival observations must be boolean, or None when unmeasured")


def survival_rates(
    trials: Iterable[SurvivalTrial], confidence: float = 0.95
) -> dict[str, dict[str, Interval | None]]:
    """Per-platform manifest and soft-binding survival, with intervals.

    This is the computation behind the study that, as of 2026-10-09, nobody has
    published. Report both columns: a platform that strips the manifest but
    preserves the soft binding is the case that makes durable bindings worth
    having, and it is invisible if you only measure manifests.
    """
    grouped: dict[str, list[SurvivalTrial]] = {}
    for t in trials:
        grouped.setdefault(t.platform, []).append(t)

    out: dict[str, dict[str, Interval | None]] = {}
    for platform, ts in sorted(grouped.items()):
        manifest = wilson(
            sum(1 for t in ts if t.manifest_survived), len(ts), confidence
        )
        sb_trials = [t for t in ts if t.soft_binding_survived is not None]
        soft = (
            wilson(
                sum(1 for t in sb_trials if t.soft_binding_survived),
                len(sb_trials),
                confidence,
            )
            if sb_trials
            else None
        )
        out[platform] = {"manifest": manifest, "soft_binding": soft}
    return out
