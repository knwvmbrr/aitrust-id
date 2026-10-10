"""INTENTIONAL CONTROL BRANCH ONLY. Never merge this test into the product."""
import pytest


def test_intentional_required_check_failure():
    pytest.fail('INTENTIONAL_NEGATIVE_CONTROL: verify main required checks block this PR')
