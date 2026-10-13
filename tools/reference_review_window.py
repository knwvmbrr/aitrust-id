"""Caller-declared time windows; never source authenticity, freshness or truth."""
from datetime import datetime, timezone
from protocol import corpus
from tools import reference_revision as revision

PROFILE = 'declared-reference-window-preflight/1.0.0'


class WindowFailure(ValueError):
    def __init__(self, category):
        self.category = category
        super().__init__('Declared reference window refused.')


def utc_now():
    return datetime.now(timezone.utc)


def preflight(record, policy, evaluated_at):
    """Validate captured policy against every attached document at an explicit clock."""
    try:
        revision.require(isinstance(evaluated_at, datetime) and evaluated_at.tzinfo is not None)
        offset = evaluated_at.utcoffset()
        revision.require(offset is not None and offset.total_seconds() == 0)
        record = corpus.parse(corpus.encoded(record))
        revision.require(type(policy) is dict)
        declared = revision.windows(policy, record, evaluated_at)
        if set(declared) != {d['id'] for d in record['documents']}:
            raise WindowFailure('review_window_missing')
        if any(state == 'not_yet_open' for state in declared.values()):
            raise WindowFailure('review_window_not_open')
        if any(state == 'elapsed' for state in declared.values()):
            raise WindowFailure('review_window_expired')
        revision.require(all(state == 'within_declared_window' for state in declared.values()))
        return {'profile': PROFILE, 'state': 'within_caller_declared_windows',
                'evaluated_at': evaluated_at.isoformat(),
                'policy_sha256': corpus.sha(corpus.encoded(policy)),
                'manifest_sha256': record['manifest_sha256'],
                'documents_checked': len(declared),
                'source_freshness_established': False, 'reviewer_authenticated': False,
                'truth_established': False, 'tag_asserted': False}
    except WindowFailure:
        raise
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError):
        raise WindowFailure('review_window_contract_refused') from None


def capture(raw):
    """Use the existing bounded duplicate-key-refusing policy decoder."""
    try:
        policy = revision.decode(raw, revision.MAX_POLICY_BYTES)
        revision.require(type(policy) is dict)
        return policy
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise WindowFailure('review_window_contract_refused') from None


def summary(before, after):
    # Public console excludes linkable hashes, IDs, exact dates and caller text.
    try:
        revision.require(type(before) is dict and type(after) is dict and before.keys() == after.keys())
        revision.require(before['profile'] == after['profile'] == PROFILE)
        revision.require({k: v for k, v in before.items() if k != 'evaluated_at'} ==
                         {k: v for k, v in after.items() if k != 'evaluated_at'})
        if datetime.fromisoformat(after['evaluated_at']) < datetime.fromisoformat(before['evaluated_at']):
            raise WindowFailure('review_clock_changed')
    except WindowFailure:
        raise
    except (ValueError, TypeError, KeyError):
        raise WindowFailure('review_window_contract_refused') from None
    return {'state': 'within_caller_declared_windows',
            'documents_checked': after['documents_checked'],
            'checked_before_and_after_comparison': True,
            'source_freshness_established': False, 'reviewer_authenticated': False}
