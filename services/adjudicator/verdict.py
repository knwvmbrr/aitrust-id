"""Experimental interpretation of supplied validation status codes.

No files, signatures, signer chains, timestamps or OCSP responses are verified
here. A trusted, version-pinned adapter must supply authenticated full results.
Unknown or incomplete verification fails closed. See docs/adjudication-spec.md."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Iterable, Sequence

SPEC_VERSION = "verdict-lattice/2.0.0"
# 2.0.0, not 1.0.1: adding UNVERIFIED shifted every ordinal above it (VALID
# 1->2, TAMPERED 6->7). docs/adjudication-spec.md section 5 makes the ordinals
# load-bearing, because severity comparison and any stored verdict depend on
# them. A consumer comparing ordinals across versions would silently
# mis-rank every state, so this is a major bump.


class Integrity(IntEnum):
    """What can be said about the asset's bytes and its claim chain.

    Ordered by severity -- an IntEnum so that `max()` over a set of
    observations yields the verdict. The ordinal values are load-bearing: edit
    them only together with the tests.
    """

    #: No manifest found. NOT a statement that the asset is untrustworthy, and
    #: NOT a statement that it is fine. Absence carries no information.
    UNSIGNED = 0

    #: A manifest is present and nothing failed, but the results do not
    #: positively establish signature validity, signer trust AND content
    #: binding together. "Nothing failed" is not "everything checked", and this
    #: state is the difference. Added 2026-10-09.
    UNVERIFIED = 1

    #: A manifest is present, cryptographically intact, and the signer chains to
    #: a configured trust anchor, with all three positive checks present. The
    #: strongest thing this module ever says.
    VALID = 2

    #: Intact, but the signer is not on the trust list in use. Says nothing
    #: about the signer's honesty -- only that we were not configured to
    #: recognise them.
    UNRECOGNIZED_SIGNER = 3

    #: Intact, but the signing certificate was outside its validity window and
    #: there is no trusted timestamp. Common and usually benign.
    EXPIRED = 4

    #: Two or more claims of equal standing disagree, or the asset carries
    #: multiple hard bindings / multiple parents. The spec explicitly declines
    #: to resolve this: "Details on how one determines which C2PA Manifest is
    #: the origin are left for specification" (Security Considerations 2.4 2.1).
    #: We do not silently pick a winner.
    CONFLICTED = 5

    #: The signing credential was revoked by its issuer. Distinct from TAMPERED:
    #: the bytes may be perfectly intact. What failed is the authority to vouch
    #: for them.
    REVOKED = 6

    #: A hard binding does not match the bytes. The asset changed after signing.
    TAMPERED = 7


class Revocation(Enum):
    """Whether revocation was established, and if not, why not.

    UNKNOWN_* are the two states that no shipped reader in this category
    surfaces, and they are the reason this enum exists. c2pa-rs defines
    `signingCredential.ocsp.skipped` as "The validator chose not to perform an
    online OCSP check" -- a statement about the validator, not the asset, which
    is exactly why it must never be rendered as a property of the asset.
    """

    #: Not meaningful: there is no credential to revoke.
    NOT_APPLICABLE = "not_applicable"

    #: Affirmatively checked and the credential is good.
    NOT_REVOKED = "not_revoked"

    #: Affirmatively checked and the credential is revoked.
    REVOKED = "revoked"

    #: We did not look. The default posture of every tool in the category.
    UNKNOWN_SKIPPED = "unknown_skipped"

    #: We looked and could not reach an answer (responder down, stapled
    #: response missing and network unavailable, CRL-only issuer).
    UNKNOWN_INACCESSIBLE = "unknown_inaccessible"

    @property
    def is_known(self) -> bool:
        return self in (
            Revocation.NOT_APPLICABLE,
            Revocation.NOT_REVOKED,
            Revocation.REVOKED,
        )


# --- C2PA status code -> observation -------------------------------------
# Codes are the string constants in c2pa-rs sdk/src/validation_results.rs.
# Anything not listed here is deliberately NOT guessed at: see `unmapped`.

_INTEGRITY_CODES: dict[str, Integrity] = {
    # Tampering: a hard binding failed.
    "assertion.dataHash.mismatch": Integrity.TAMPERED,
    "assertion.bmffHash.mismatch": Integrity.TAMPERED,
    "assertion.boxesHash.mismatch": Integrity.TAMPERED,
    "assertion.generalBoxesHash.mismatch": Integrity.TAMPERED,
    "claimSignature.mismatch": Integrity.TAMPERED,
    # Revocation also lands on the integrity axis so that severity ordering
    # works, but the authoritative revocation fact is the second element of the
    # pair. Both are set; neither is inferred from the other.
    "signingCredential.ocsp.revoked": Integrity.REVOKED,
    # Conflict: the spec's own unresolved case.
    "claim.multiple": Integrity.CONFLICTED,
    "assertion.multipleHardBindings": Integrity.CONFLICTED,
    "manifest.multipleParents": Integrity.CONFLICTED,
    "manifest.update.wrongParents": Integrity.CONFLICTED,
    # Credential lifecycle.
    "signingCredential.expired": Integrity.EXPIRED,
    "signingCredential.untrusted": Integrity.UNRECOGNIZED_SIGNER,
    "timeStamp.untrusted": Integrity.UNRECOGNIZED_SIGNER,
}

_REVOCATION_CODES: dict[str, Revocation] = {
    "signingCredential.ocsp.revoked": Revocation.REVOKED,
    "signingCredential.ocsp.notRevoked": Revocation.NOT_REVOKED,
    "signingCredential.ocsp.skipped": Revocation.UNKNOWN_SKIPPED,
    "signingCredential.ocsp.inaccessible": Revocation.UNKNOWN_INACCESSIBLE,
}

#: Codes we recognise as benign/informational. Listed explicitly so that an
#: unknown code is never silently treated as success.
_BENIGN_CODES: frozenset[str] = frozenset(
    {
        "claimSignature.validated",
        "signingCredential.trusted",
        "timeStamp.validated",
        "timeStamp.trusted",
        "assertion.hashedURI.match",
        "assertion.dataHash.match",
        "assertion.bmffHash.match",
        "assertion.accessible",
        "claim.signing.validated",
        "signingCredential.ocsp.notRevoked",
    }
)

_PLAIN_LANGUAGE: dict[Integrity, str] = {
    Integrity.UNSIGNED: (
        "No provenance credential was found. That is not evidence the content is "
        "fake, and not evidence it is genuine — most content carries no credential."
    ),
    Integrity.UNVERIFIED: (
        "The supplied results do not establish complete signature, signer-trust "
        "and content-binding verification. No positive assurance is available."
    ),
    Integrity.VALID: (
        "A provenance credential is present, the content matches what was signed, "
        "and the signer is on the trust list in use."
    ),
    Integrity.UNRECOGNIZED_SIGNER: (
        "The supplied results report a signer not on the trust "
        "list in use. This says nothing about the signer's honesty."
    ),
    Integrity.EXPIRED: (
        "The supplied results report that the signing certificate was "
        "outside its validity period and no trusted timestamp was present."
    ),
    Integrity.CONFLICTED: (
        "Two or more provenance claims of equal standing disagree about this "
        "content. No rule resolves which one is authoritative, so none is "
        "presented as the answer."
    ),
    Integrity.REVOKED: (
        "The credential that signed this content was revoked by its issuer. The "
        "bytes may be intact; the authority to vouch for them is withdrawn."
    ),
    Integrity.TAMPERED: (
        "Content binding or signature verification failed. This does not establish when, why, or by whom content changed."
    ),
}

_REVOCATION_LANGUAGE: dict[Revocation, str] = {
    Revocation.NOT_APPLICABLE: "",
    Revocation.NOT_REVOKED: "The supplied revocation result reports not revoked; freshness and issuer verification belong to the upstream validator.",
    Revocation.REVOKED: "Revocation was checked: the credential is revoked.",
    Revocation.UNKNOWN_SKIPPED: (
        "Revocation was NOT checked. A revoked credential would look identical to "
        "a current one here."
    ),
    Revocation.UNKNOWN_INACCESSIBLE: (
        "Revocation could not be checked — the status service was unreachable. A "
        "revoked credential would look identical to a current one here."
    ),
}


def _complete_verification(codes: Iterable[str]) -> bool:
    codes = set(codes)
    return ("claimSignature.validated" in codes and "signingCredential.trusted" in codes
            and bool(codes & {"assertion.dataHash.match", "assertion.bmffHash.match"}))


class UnmappedStatusCode(ValueError):
    """Raised when a status code is neither mapped nor explicitly benign.

    Failing loudly is the point. The alternative -- treating an unrecognised
    code as success -- is how a validator ends up reporting a revoked
    certificate as valid.
    """


@dataclass(frozen=True)
class Verdict:
    integrity: Integrity
    revocation: Revocation
    codes: tuple[str, ...] = ()
    #: Codes that were recognised but contributed nothing (benign/informational).
    benign: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.integrity, Integrity) or not isinstance(self.revocation, Revocation):
            raise ValueError("Verdict requires typed integrity and revocation states")
        if self.integrity is Integrity.UNSIGNED and self.revocation is not Revocation.NOT_APPLICABLE:
            raise ValueError("An unsigned asset has no credential revocation state")
        if self.integrity is not Integrity.UNSIGNED and self.revocation is Revocation.NOT_APPLICABLE:
            raise ValueError("A present credential requires a revocation assessment")
        if (self.integrity is Integrity.REVOKED or self.revocation is Revocation.REVOKED) and not (
            self.revocation is Revocation.REVOKED and self.integrity >= Integrity.REVOKED
        ):
            raise ValueError("Revoked integrity and revocation must agree")
        if self.integrity is Integrity.VALID and not _complete_verification(self.codes):
            raise ValueError("VALID requires explicit signature, signer trust and content binding success codes")

    @property
    def is_asserted(self) -> bool:
        """True only when this verdict may be shown as a positive assurance.

        VALID alone is not enough. If revocation is unknown, there is no
        assurance to assert -- there is a measurement we declined to take.
        """
        return self.integrity is Integrity.VALID and self.revocation is Revocation.NOT_REVOKED and not self.notes

    @property
    def state(self) -> str:
        """Stable machine-readable state string for logs, tests and the tag API."""
        if self.integrity is Integrity.VALID and not self.revocation.is_known:
            return "valid_revocation_unknown"
        return self.integrity.name.lower()

    def render(self) -> str:
        """The sentence a user sees. Never omits an unknown revocation state."""
        parts = [_PLAIN_LANGUAGE[self.integrity]]
        rev = _REVOCATION_LANGUAGE[self.revocation]
        if rev:
            parts.append(rev)
        parts.extend(self.notes)
        return " ".join(p for p in parts if p)

    def to_dict(self) -> dict:
        return {
            "spec_version": SPEC_VERSION,
            "state": self.state,
            "integrity": self.integrity.name,
            "revocation": self.revocation.value,
            "revocation_known": self.revocation.is_known,
            "asserted": self.is_asserted,
            "codes": list(self.codes),
            "benign_codes": list(self.benign),
            "message": self.render(),
        }


def from_status_codes(
    codes: Iterable[str],
    *,
    manifest_present: bool = True,
    ocsp_checked: bool | None = None,
    strict: bool = True,
) -> Verdict:
    """Map a validator's status codes to a (integrity, revocation) verdict.

    Args:
      codes: status code strings, e.g. from c2pa-rs `validation_results`. Pass
        the *full* results, not the lossy `validation_status` failures-only
        field -- success codes carry the revocation evidence.
      manifest_present: False when no manifest store was found at all.
      ocsp_checked: tri-state observation for validators that do not emit an OCSP
        code. None means "the codes decide". False means the validator is known
        not to have checked (e.g. c2pa-rs with its default `ocsp_fetch: false`
        and no stapled response), which yields UNKNOWN_SKIPPED rather than
        silently implying a clean check.
      strict: raise on an unrecognised code. Turning this off is a deliberate,
        auditable choice and records a note on the verdict.

    Raises:
      UnmappedStatusCode: when strict and a code is unrecognised.
    """
    codes = tuple(codes)

    if not manifest_present:
        if codes:
            raise ValueError(
                "manifest_present=False but status codes were supplied: "
                f"{codes!r}. An absent manifest cannot produce validation codes."
            )
        return Verdict(Integrity.UNSIGNED, Revocation.NOT_APPLICABLE)

    observed: list[Integrity] = []
    revocation: Revocation | None = None
    benign: list[str] = []
    unknown: list[str] = []

    for code in codes:
        matched = False
        if code in _REVOCATION_CODES:
            candidate = _REVOCATION_CODES[code]
            # A positive revocation finding always wins over any other
            # revocation observation; otherwise first-seen wins.
            priority = {Revocation.NOT_REVOKED: 0, Revocation.UNKNOWN_SKIPPED: 1,
                        Revocation.UNKNOWN_INACCESSIBLE: 2, Revocation.REVOKED: 3}
            if revocation is None or priority[candidate] > priority[revocation]:
                revocation = candidate
            matched = True
        if code in _INTEGRITY_CODES:
            observed.append(_INTEGRITY_CODES[code])
            matched = True
        if matched:
            continue
        if code in _BENIGN_CODES:
            benign.append(code)
            continue
        unknown.append(code)

    notes: list[str] = []
    if unknown:
        if strict:
            raise UnmappedStatusCode(
                "Unrecognised validation status code(s): "
                f"{sorted(unknown)!r}. Refusing to guess — an unmapped code "
                "treated as success is how a revoked credential gets reported "
                "as valid. Add it to _INTEGRITY_CODES, _REVOCATION_CODES or "
                "_BENIGN_CODES."
            )
        notes.append(
            f"{len(unknown)} validation code(s) were not recognised by this "
            "version and were not interpreted."
        )

    if ocsp_checked is False and revocation in (None, Revocation.NOT_REVOKED):
        # The validator told us it did not check. That overrides an optimistic
        # reading, and it cannot override a positive REVOKED finding.
        revocation = Revocation.UNKNOWN_SKIPPED
    elif ocsp_checked is True and revocation is None:
        # Attempting a check does not establish its outcome.
        revocation = Revocation.UNKNOWN_INACCESSIBLE

    if revocation is None:
        # No code spoke to revocation and the caller gave no override. The
        # honest reading is that nobody checked -- NOT that it is fine.
        revocation = Revocation.UNKNOWN_SKIPPED

    integrity = max(observed) if observed else (
        Integrity.VALID if _complete_verification(codes) and not unknown else Integrity.UNVERIFIED
    )

    # Consistency guard: these two facts are set independently, so assert they
    # agree rather than deriving one from the other and hiding a mismatch.
    if revocation is Revocation.REVOKED and integrity < Integrity.REVOKED:
        integrity = Integrity.REVOKED
    if integrity is Integrity.REVOKED and revocation is not Revocation.REVOKED:
        raise ValueError(
            "integrity=REVOKED requires revocation=REVOKED; got "
            f"{revocation!r}. This pairing must never be inferred."
        )

    return Verdict(
        integrity=integrity,
        revocation=revocation,
        codes=codes,
        benign=tuple(benign),
        notes=tuple(notes),
    )


def worst(verdicts: Sequence[Verdict]) -> Verdict:
    """Combine per-manifest verdicts for an asset with several manifests.

    Severity wins, and an unknown revocation anywhere makes the whole asset's
    revocation unknown -- you cannot average your way to an assurance.
    """
    if not verdicts:
        raise ValueError("worst() requires at least one verdict")
    chosen = max(verdicts, key=lambda v: v.integrity.value)
    if any(v.revocation is Revocation.REVOKED for v in verdicts):
        rev = Revocation.REVOKED
    elif all(v.revocation.is_known for v in verdicts):
        rev = chosen.revocation
    else:
        rev = next(v.revocation for v in verdicts if not v.revocation.is_known)
    integrity = chosen.integrity
    if integrity is Integrity.VALID and any(v.integrity is Integrity.UNVERIFIED or v.notes for v in verdicts):
        integrity = Integrity.UNVERIFIED
    if rev is Revocation.REVOKED and integrity < Integrity.REVOKED:
        integrity = Integrity.REVOKED
    return Verdict(
        integrity=integrity,
        revocation=rev,
        codes=tuple(c for v in verdicts for c in v.codes),
        benign=tuple(c for v in verdicts for c in v.benign),
        notes=tuple(n for v in verdicts for n in v.notes),
    )
