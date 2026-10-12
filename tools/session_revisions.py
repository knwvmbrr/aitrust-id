"""Selected literal revision context; never authorship or semantic derivation."""
import hashlib
import json
from pathlib import Path
from protocol import corpus
from protocol.normalization import normalize_nfc, NORMALIZATION_ID

METHOD = "selected-context-revision/1.0.0"
PROFILE = "selected-revision-spans/1.0.0"
MAX_CHARACTERS = 8000
MAX_SELECTIONS = 32
MAX_SELECTION_BYTES = 16384

class ContextError(ValueError):
    pass

def require(value):
    if not value:
        raise ContextError("Selected private revision contract refused.")

def subject(value, allow_empty=False):
    require(type(allow_empty) is bool)
    require(type(value) is str and (allow_empty or value.strip()) and len(value) <= MAX_CHARACTERS and "\x00" not in value)
    try:
        value.encode("utf-8", "strict")
        normalized = normalize_nfc(value)
        require(len(normalized) <= MAX_CHARACTERS)
        return normalized
    except (UnicodeError, ValueError):
        raise ContextError("Selected private revision contract refused.") from None

def digest(value):
    return hashlib.sha256(value.encode("utf-8", "strict")).hexdigest()

def decode(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_SELECTION_BYTES)
    def refuse(_):
        raise ContextError("Selected private revision contract refused.")
    try:
        return json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=corpus.unique_pairs,
                          parse_float=refuse, parse_constant=refuse)
    except (ValueError, UnicodeError, RecursionError):
        raise ContextError("Selected private revision contract refused.") from None

def compare(previous, current, captured, selections):
    previous = subject(previous, allow_empty=True)
    current = subject(current)
    captured = corpus.parse(captured)
    require(type(selections) is dict and set(selections) == {"profile", "previous_sha256", "current_sha256", "context_manifest_sha256", "spans"})
    require(selections["profile"] == PROFILE and selections["previous_sha256"] == digest(previous)
            and selections["current_sha256"] == digest(current)
            and selections["context_manifest_sha256"] == captured["manifest_sha256"])
    spans = selections["spans"]
    require(type(spans) is list and 1 <= len(spans) <= MAX_SELECTIONS)
    documents = [(d["id"], d["sha256"], normalize_nfc(d["text"])) for d in captured["documents"]]
    rows = []
    end_of_previous_selection = 0
    for span in spans:
        require(type(span) is list and len(span) == 2 and all(type(i) is int for i in span))
        left, right = span
        require(0 <= left < right <= len(current) and left >= end_of_previous_selection)
        end_of_previous_selection = right
        literal = current[left:right]
        require(literal.strip())
        old_location = previous.find(literal)
        matches = []
        for identity, sha, text in documents:
            location = text.find(literal)
            if location >= 0:
                matches.append({"document_id": identity, "raw_document_sha256": sha,
                    "normalized_document_sha256": digest(text), "first_span": [location, location + len(literal)]})
        rows.append({"current_span": list(span), "selected_literal_sha256": digest(literal),
            "present_in_previous_revision": old_location >= 0,
            "first_previous_span": [old_location, old_location + len(literal)] if old_location >= 0 else None,
            "captured_context_matches": matches,
            "new_literal_not_located_in_captured_context": old_location < 0 and not matches})
    return {"method": METHOD, "method_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "normalization": NORMALIZATION_ID, "span_units": "NFC_unicode_codepoints",
        "previous_sha256": digest(previous), "current_sha256": digest(current),
        "context_manifest_sha256": captured["manifest_sha256"], "selection_sha256": corpus.sha(corpus.encoded(selections)),
        "selected_spans": rows, "matching": "first_exact_case_sensitive_normalized_literal_per_document",
        "selection_source": "explicit_caller_selection", "source_completeness_verified": False,
        "context_origin_authenticated": False, "semantic_derivation_assessed": False,
        "human_authorship_established": False, "ai_authorship_established": False,
        "outside_knowledge_established": False, "tag_asserted": False,
        "independent_accuracy_evidence": False, "network_used": False}

def prepare(previous, current, captured, spans):
    """Bind caller-selected spans; validate with the same comparison contract."""
    previous = subject(previous, allow_empty=True)
    current = subject(current)
    context = corpus.parse(captured)
    require(type(spans) is list)
    selections = {"profile": PROFILE, "previous_sha256": digest(previous),
        "current_sha256": digest(current),
        "context_manifest_sha256": context["manifest_sha256"],
        "spans": [list(span) if type(span) is list else span for span in spans]}
    compare(previous, current, captured, selections)
    return selections

def summary(result, details_written=False):
    require(type(details_written) is bool)
    rows = result["selected_spans"]
    new = sum(not r["present_in_previous_revision"] for r in rows)
    missing = sum(r["new_literal_not_located_in_captured_context"] for r in rows)
    return {"state": "selected_literals_compared", "selected_spans": len(rows),
        "literals_already_in_previous_revision": len(rows)-new,
        "new_literals_located_in_captured_context": new-missing,
        "new_literals_not_located_in_captured_context": missing,
        "private_details_written": details_written,
        "next_step": "Review the selected wording and supplied context; literal absence does not establish origin or knowledge.",
        "outside_knowledge_established": False, "semantic_derivation_assessed": False, "tag_asserted": False}
