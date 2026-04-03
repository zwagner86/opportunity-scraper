from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone


WHITESPACE_RE = re.compile(r"\s+")


def compact_whitespace(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value or "").strip()


def normalize_for_hash(*parts: str) -> str:
    normalized = " || ".join(compact_whitespace(part).lower() for part in parts if part)
    return normalized


def make_dedupe_hash(*parts: str) -> str:
    payload = normalize_for_hash(*parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def make_short_hash(*parts: str, length: int = 12) -> str:
    return make_dedupe_hash(*parts)[:length]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
