#!/usr/bin/env python3
"""Bind explicitly chosen NFC codepoint spans to private drafts and context."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from protocol import corpus
from tools import session_revisions as tool
from tools.blind_review_io import PacketError, source, create


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "Selection preparation refused; use --help for arguments.\n")


def main(argv=None):
    parser = Parser(description=__doc__)
    for name in ("previous", "current", "context", "spans", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        previous = source(args.previous, ROOT, 32768).decode("utf-8", "strict")
        current = source(args.current, ROOT, 32768).decode("utf-8", "strict")
        captured = source(args.context, ROOT, corpus.MAX_STORE_BYTES)
        spans = tool.decode(source(args.spans, ROOT, tool.MAX_SELECTION_BYTES))
        selections = tool.prepare(previous, current, captured, spans)
        create(args.output, ROOT, {"selections.json": corpus.encoded(selections)})
        print(json.dumps({"state": "private_selections_bound", "selected_spans": len(spans),
                          "automatic_capture": False, "tag_asserted": False}))
        return 0
    except (tool.ContextError, corpus.CorpusError, PacketError, OSError, UnicodeError,
            ValueError, TypeError, RecursionError):
        print(json.dumps({"state": "UNAVAILABLE", "reason": "private_selection_preparation_refused",
                          "tag_asserted": False}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
