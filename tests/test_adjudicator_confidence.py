"""Supplied confidence is numeric input, never independent evidence."""
import importlib.util
import sys
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "confidence_contract_adjudicate",
    Path(__file__).resolve().parents[1] / "services/adjudicator/adjudicate.py",
)
A = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = A
spec.loader.exec_module(A)


class FloatSubclass(float):
    pass


class ComparisonTrap:
    def __ge__(self, other):
        raise AssertionError("Invalid input must not execute custom comparisons")


INVALID = [True, False, -1, 2, -0.001, 1.001, float("nan"), float("inf"),
           -float("inf"), "0.9", "private-example-do-not-echo", [], {},
           Decimal("0.9"), Fraction(1, 2), FloatSubclass(0.5), ComparisonTrap(),
           10**1000, -(10**1000)]


@pytest.mark.parametrize("confidence", INVALID)
@pytest.mark.parametrize("layer", [A.Layer.CLASSIFIER, A.Layer.METADATA])
def test_invalid_confidence_refused_without_echo_or_coercion(confidence, layer):
    with pytest.raises(ValueError) as error:
        A.Signal(layer, "origin", "ai", "supplied-observation", confidence=confidence)
    assert str(error.value) == "Signal.confidence must be a finite number in [0,1]"


@pytest.mark.parametrize("confidence", [0, 1, 0.0, -0.0, 1.0, 0.5])
def test_classifier_score_never_asserts_or_contests(confidence):
    classifier = A.Signal(A.Layer.CLASSIFIER, "origin", "ai", "classifier",
                          confidence=confidence)
    manifest = A.Signal(A.Layer.MANIFEST, "origin", "human", "manifest",
                        verified=True, verdict_state="valid")
    assert classifier.standing == 0
    assert not classifier.may_assert and not classifier.may_contest
    assert A.adjudicate([classifier], claim="origin").outcome is A.Outcome.UNSUPPORTED
    result = A.adjudicate([manifest, classifier], claim="origin")
    assert result.outcome is A.Outcome.SUPPORTED and result.value == "human"
    assert not result.overruled and not result.contradiction
    assert result.to_dict()["spec_version"] == "adjudication/1.0.2"


def test_missing_classifier_score_still_refused():
    with pytest.raises(ValueError, match="must carry a confidence"):
        A.Signal(A.Layer.CLASSIFIER, "origin", "ai", "classifier")


@pytest.mark.parametrize("confidence", [None, 0, 1, 0.5])
def test_optional_metadata_score_cannot_gain_assertion_authority(confidence):
    metadata = A.Signal(A.Layer.METADATA, "origin", "human", "unsigned-metadata",
                        confidence=confidence)
    assert metadata.standing == 1 and not metadata.may_assert
    assert A.adjudicate([metadata], claim="origin").outcome is A.Outcome.UNSUPPORTED
