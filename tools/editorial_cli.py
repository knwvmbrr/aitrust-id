"""Deliberate private file operations for editorial review; no network or evaluation."""
import argparse
import json
import os
from pathlib import Path
from tools.blind_review_io import directory, member, source, create, PacketError
from tools import newsroom


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'Editorial command refused; use --help for the required private files and review choice.\n')


def read_packet(path, root, supersede=False):
    with directory(path, root) as fd:
        expected = {'source.json', 'subject.txt', 'review.json'} | ({'previous.json'} if supersede else set())
        newsroom.require(set(os.listdir(fd)) == expected)
        raw = member(fd, 'source.json', 2_000_000)
        source_format, _, _, _, _ = newsroom.inspect_source(newsroom.parse(raw, 2_000_000), root)
        result = [raw, member(fd, 'subject.txt', newsroom.SUBJECT_LIMITS[source_format][1]),
                  member(fd, 'review.json', 16_384)]
        previous = member(fd, 'previous.json', 2_000_000) if supersede else None
    return result, previous


def run(argv, root):
    parser = Parser(description='Make a private editorial view of a selected existing finding. Does not check new text, upload data or change a tag.')
    parser.add_argument('--packet', type=Path, required=True, help='Owner-private packet prepared with prepare-editorial-review.py.')
    parser.add_argument('--output', type=Path, required=True, help='New private output directory outside the checkout; never overwrite.')
    parser.add_argument('--reviewed-record', action='store_true', help='Use only after reading the selected source record and text.')
    parser.add_argument('--supersede', action='store_true', help='Require the explicitly selected prior private journal in this packet.')
    parser.add_argument('--include-subject', action='store_true', help='Separately include evaluated text in the private HTML. Review privacy before sharing.')
    a = parser.parse_args(argv)
    try:
        newsroom.require(a.reviewed_record is True)
        args, previous = read_packet(a.packet, root, a.supersede)
        record, text = newsroom.analyze(*args, root=root, raw_previous=previous)
        record['subject_included'] = a.include_subject
        create(a.output, root, {'editorial-review.json': newsroom.encode(record),
                              'editorial-review.html': newsroom.render(record, text if a.include_subject else None)})
        print(json.dumps({'created': True, 'decision': newsroom.DECISIONS[record['decision']],
                          'source_findings': [row['code'] for row in record['source_tags']],
                          'source_format': record['source_format'], 'subject_included': a.include_subject,
                          'meaning': 'Editor decision saved separately from the source finding. This does not verify content truth or tag accuracy.',
                          'network_used': False, 'automatic_collection': False, 'tag_release_approved': False}))
        return 0
    except (ValueError, OSError, KeyError, TypeError, RuntimeError, RecursionError, PacketError):
        print(json.dumps({'state': 'UNAVAILABLE', 'reason': 'invalid_private_editorial_packet',
                          'next_step': 'Check the supported source format, current method, matching evaluated text, private permissions and new output folder.',
                          'network_used': False, 'tag_release_approved': False}), file=__import__('sys').stderr)
        return 2


def prepare(argv, root):
    parser = Parser(description='Prepare private editorial review from files you select. Source must be a current detailed PS browser record or current unsigned gateway wire record. A share summary is insufficient.')
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--subject', type=Path, required=True, help='Exact text evaluated by the selected source; gateway subject is already redacted.')
    parser.add_argument('--reviewer', required=True, help='Declared private handle, lowercase letters/digits/_/-, 3–64 characters. Not authenticated.')
    parser.add_argument('--decision', required=True, choices=sorted(newsroom.DECISIONS))
    parser.add_argument('--reason', required=True, choices=sorted(newsroom.REASONS))
    parser.add_argument('--previous', type=Path, help='Optional prior editorial-review.json; use a new output to retain history.')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reviewed-record', action='store_true')
    a = parser.parse_args(argv)
    try:
        newsroom.require(a.reviewed_record is True)
        raw = source(a.source, root, 2_000_000)
        source_format, subject, _, _, _ = newsroom.inspect_source(newsroom.parse(raw, 2_000_000), root)
        text = source(a.subject, root, newsroom.SUBJECT_LIMITS[source_format][1])
        previous = source(a.previous, root, 2_000_000) if a.previous else None
        selection = {'profile': newsroom.PROFILE, 'assertion_sha256': newsroom.sha(raw),
                     'subject_sha256': subject['sha256'], 'reviewer_handle': a.reviewer,
                     'decision': a.decision, 'reason': a.reason,
                     'previous_record_sha256': newsroom.sha(previous) if previous else None}
        selected = newsroom.encode(selection)
        newsroom.analyze(raw, text, selected, root=root, raw_previous=previous)
        files = {'source.json': raw, 'subject.txt': text, 'review.json': selected}
        if previous is not None: files['previous.json'] = previous
        create(a.output, root, files)
        print(json.dumps({'prepared': True, 'prior_record_selected': previous is not None,
                          'next_step': 'Read review.json, then run editorial-review.py with --reviewed-record. Add --supersede only if a prior record was selected.',
                          'source_rewritten': False, 'network_used': False, 'tag_release_approved': False}))
        return 0
    except (ValueError, OSError, KeyError, TypeError, RuntimeError, RecursionError, PacketError):
        print('Editorial preparation unavailable. Check selected files, supported identities, private permissions and a new destination.', file=__import__('sys').stderr)
        return 2
