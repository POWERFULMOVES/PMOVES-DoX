"""PII detection and CHIT-based field-level masking for UNFCU DoX.

Provides regex + NER augmented PII detection and two masking modes:
  - ``redact``: replace with format-preserving display tokens (irreversible)
  - ``encrypt``: replace with AES-256-GCM ciphertext (recoverable with passphrase)

The encryption reuses the PBKDF2 + AES-GCM pattern from
``pmoves/tools/chit_security.py`` but operates on UTF-8 strings instead of
float arrays.
"""

from __future__ import annotations

import base64
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Crypto helpers (mirror chit_security._derive_key)
# ---------------------------------------------------------------------------
try:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    _CRYPTO_OK = True
except ImportError:
    _CRYPTO_OK = False


def _derive_key(passphrase: str, salt: bytes, length: int = 32) -> bytes:
    if not _CRYPTO_OK:
        raise RuntimeError("cryptography package not installed")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=length, salt=salt, iterations=600_000
    )
    return kdf.derive(passphrase.encode("utf-8"))


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class PIIMatch:
    """A single PII detection in text."""

    start: int
    end: int
    text: str
    pii_type: str
    confidence: float = 1.0
    source: str = "regex"  # "regex" | "ner"


@dataclass
class EncryptedField:
    """An AES-GCM encrypted PII field."""

    pii_type: str
    original_text: str  # only populated server-side, never serialized to client
    display_token: str
    ciphertext_b64: str
    iv_b64: str
    salt_b64: str


# ---------------------------------------------------------------------------
# PII patterns
# ---------------------------------------------------------------------------

def _mask_ssn(text: str) -> str:
    """``123-45-6789`` → ``***-**-6789``"""
    digits = re.sub(r"\D", "", text)
    return f"***-**-{digits[-4:]}" if len(digits) >= 4 else "***-**-****"


def _mask_account(text: str) -> str:
    """``12345678`` → ``****5678``"""
    digits = re.sub(r"\D", "", text)
    return f"****{digits[-4:]}" if len(digits) >= 4 else "****"


def _mask_credit_card(text: str) -> str:
    """``4111111111111111`` → ``****-****-****-1111``"""
    digits = re.sub(r"\D", "", text)
    return f"****-****-****-{digits[-4:]}" if len(digits) >= 4 else "****-****-****-****"


def _mask_routing(text: str) -> str:
    return "****" + re.sub(r"\D", "", text)[-4:]


def _mask_email(text: str) -> str:
    """``john@example.com`` → ``j***@example.com``"""
    parts = text.split("@")
    if len(parts) == 2:
        local = parts[0]
        masked_local = local[0] + "***" if local else "***"
        return f"{masked_local}@{parts[1]}"
    return "***@***.***"


def _mask_phone(text: str) -> str:
    digits = re.sub(r"\D", "", text)
    return f"(***) ***-{digits[-4:]}" if len(digits) >= 4 else "(***) ***-****"


def _mask_person(text: str) -> str:
    """``John Smith`` → ``J*** S***``"""
    parts = text.split()
    return " ".join(p[0] + "***" if p else "***" for p in parts)


def _luhn_check(num_str: str) -> bool:
    """Validate credit card number with Luhn algorithm."""
    digits = [int(d) for d in num_str if d.isdigit()]
    if len(digits) < 13:
        return False
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


@dataclass
class PIIPattern:
    """Defines a PII detection regex and its mask function."""

    name: str
    regex: str
    mask_fn: Any  # Callable[[str], str]
    entity_type: str = "PII"
    validate_fn: Any = None  # Optional extra validation


# Built-in patterns ordered by specificity (most specific first)
BUILTIN_PATTERNS: List[PIIPattern] = [
    PIIPattern(
        name="SSN",
        regex=r"\b\d{3}-\d{2}-\d{4}\b",
        mask_fn=_mask_ssn,
        entity_type="SSN",
    ),
    PIIPattern(
        name="CREDIT_CARD",
        regex=r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{1,4}\b",
        mask_fn=_mask_credit_card,
        entity_type="CREDIT_CARD",
        validate_fn=lambda t: _luhn_check(re.sub(r"\D", "", t)),
    ),
    PIIPattern(
        name="ROUTING_NUMBER",
        regex=r"(?i)(?:routing|aba|rtn)[:\s#]*(\d{9})\b",
        mask_fn=_mask_routing,
        entity_type="ROUTING_NUMBER",
    ),
    PIIPattern(
        name="EMAIL",
        regex=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        mask_fn=_mask_email,
        entity_type="EMAIL",
    ),
    PIIPattern(
        name="PHONE_US",
        regex=r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b",
        mask_fn=_mask_phone,
        entity_type="PHONE_US",
    ),
    PIIPattern(
        name="ACCOUNT_NUMBER",
        regex=r"(?i)(?:account|acct|member|a/c)[\s#:.-]*(\d{8,17})\b",
        mask_fn=_mask_account,
        entity_type="ACCOUNT_NUMBER",
    ),
]


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def detect_pii(
    text: str,
    ner_entities: Optional[List[Dict[str, Any]]] = None,
    patterns: Optional[List[PIIPattern]] = None,
) -> List[PIIMatch]:
    """Detect PII in *text* using regex patterns and optional NER entities.

    Args:
        text: The input text to scan.
        ner_entities: Optional list of NER entity dicts (from ``NERProcessor``)
            with keys ``text``, ``label``, ``start_char``, ``end_char``.
        patterns: Custom pattern list; defaults to ``BUILTIN_PATTERNS``.

    Returns:
        De-duplicated list of ``PIIMatch`` sorted by span start.
    """
    if not text:
        return []

    patterns = patterns or BUILTIN_PATTERNS
    matches: List[PIIMatch] = []
    occupied: List[tuple[int, int]] = []  # prevent overlapping matches

    def _overlaps(start: int, end: int) -> bool:
        return any(s < end and start < e for s, e in occupied)

    # 1. Regex-based detection
    for pat in patterns:
        for m in re.finditer(pat.regex, text):
            # Use capture group if present, otherwise full match
            if m.lastindex:
                start, end = m.start(1), m.end(1)
                matched_text = m.group(1)
            else:
                start, end = m.start(), m.end()
                matched_text = m.group()
            if _overlaps(start, end):
                continue
            if pat.validate_fn and not pat.validate_fn(matched_text):
                continue
            matches.append(
                PIIMatch(
                    start=start,
                    end=end,
                    text=matched_text,
                    pii_type=pat.name,
                    confidence=0.95,
                    source="regex",
                )
            )
            occupied.append((start, end))

    # 2. NER augmentation (PERSON entities)
    if ner_entities:
        for ent in ner_entities:
            if ent.get("label") != "PERSON":
                continue
            ent_text = ent.get("text", "")
            if not ent_text or len(ent_text) < 2:
                continue
            # Find this entity in the text
            idx = text.find(ent_text)
            while idx != -1:
                end_idx = idx + len(ent_text)
                if not _overlaps(idx, end_idx):
                    matches.append(
                        PIIMatch(
                            start=idx,
                            end=end_idx,
                            text=ent_text,
                            pii_type="PERSON_NAME",
                            confidence=0.85,
                            source="ner",
                        )
                    )
                    occupied.append((idx, end_idx))
                idx = text.find(ent_text, end_idx)

    matches.sort(key=lambda m: m.start)
    return matches


# ---------------------------------------------------------------------------
# Masking
# ---------------------------------------------------------------------------

_MASK_FN_MAP = {p.name: p.mask_fn for p in BUILTIN_PATTERNS}
_MASK_FN_MAP["PERSON_NAME"] = _mask_person


def mask_text(
    text: str,
    matches: List[PIIMatch],
    mode: str = "redact",
) -> str:
    """Replace PII spans in *text* with display tokens.

    Args:
        text: Original text.
        matches: Sorted ``PIIMatch`` list from ``detect_pii``.
        mode: ``"redact"`` for display tokens only.

    Returns:
        Masked text string.
    """
    if not matches:
        return text

    parts: List[str] = []
    prev_end = 0
    for m in sorted(matches, key=lambda m: m.start):
        parts.append(text[prev_end : m.start])
        mask_fn = _MASK_FN_MAP.get(m.pii_type, lambda t: "****")
        parts.append(mask_fn(m.text))
        prev_end = m.end
    parts.append(text[prev_end:])
    return "".join(parts)


# ---------------------------------------------------------------------------
# Field-level encryption
# ---------------------------------------------------------------------------

def encrypt_pii_fields(
    matches: List[PIIMatch],
    passphrase: str,
) -> List[Dict[str, str]]:
    """Encrypt each PII match individually with AES-256-GCM.

    Args:
        matches: PII detections from ``detect_pii``.
        passphrase: CHIT passphrase (usually ``CHIT_PASSPHRASE`` env var).

    Returns:
        List of encrypted field dicts with keys:
        ``pii_type``, ``display_token``, ``ciphertext``, ``iv``, ``salt``.
    """
    if not _CRYPTO_OK:
        raise RuntimeError("cryptography package not installed — cannot encrypt PII")

    results: List[Dict[str, str]] = []
    for m in matches:
        salt = os.urandom(16)
        iv = os.urandom(12)
        key = _derive_key(passphrase, salt)
        aead = AESGCM(key)
        ct = aead.encrypt(iv, m.text.encode("utf-8"), None)

        mask_fn = _MASK_FN_MAP.get(m.pii_type, lambda t: "****")
        results.append({
            "pii_type": m.pii_type,
            "display_token": mask_fn(m.text),
            "ciphertext": base64.b64encode(ct).decode("ascii"),
            "iv": base64.b64encode(iv).decode("ascii"),
            "salt": base64.b64encode(salt).decode("ascii"),
        })
    return results


def decrypt_pii_field(
    encrypted: Dict[str, str],
    passphrase: str,
) -> str:
    """Decrypt a single encrypted PII field.

    Args:
        encrypted: Dict with ``ciphertext``, ``iv``, ``salt`` keys (base64).
        passphrase: CHIT passphrase.

    Returns:
        Original plaintext string.
    """
    if not _CRYPTO_OK:
        raise RuntimeError("cryptography package not installed")

    salt = base64.b64decode(encrypted["salt"])
    iv = base64.b64decode(encrypted["iv"])
    ct = base64.b64decode(encrypted["ciphertext"])
    key = _derive_key(passphrase, salt)
    aead = AESGCM(key)
    return aead.decrypt(iv, ct, None).decode("utf-8")


__all__ = [
    "PIIMatch",
    "PIIPattern",
    "BUILTIN_PATTERNS",
    "detect_pii",
    "mask_text",
    "encrypt_pii_fields",
    "decrypt_pii_field",
]
