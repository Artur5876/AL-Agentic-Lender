"""Audit hash of a decision record (US-331).

The same record must always produce the same bytes, whatever order its keys were built in,
so the hash stored on-chain can be recomputed later from Firestore and compared:

    canonical_json(record) -> str   sorted keys, no spaces, UTF-8 (not \\u escapes),
                                    datetimes as ISO 8601 UTC, NaN/Infinity rejected
    audit_hash(record)     -> str   SHA-256 hex digest (64 chars) of that string

No Firebase, FastAPI or web3 imports, so it can be tested on its own.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime


def _utc_iso(value: datetime) -> str:
    """ISO 8601 in UTC, e.g. 2026-11-13T14:02:11.123456+00:00.

    Rebuilt as a plain datetime so Firestore's DatetimeWithNanoseconds subclass and an
    equal datetime in another timezone give exactly the same text.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        raise TypeError("Naive datetime in audit record; use timezone-aware UTC datetimes.")
    u = value.astimezone(UTC)
    plain = datetime(u.year, u.month, u.day, u.hour, u.minute, u.second, u.microsecond,
                     tzinfo=UTC)
    return plain.isoformat()


def _default(value: object) -> str:
    if isinstance(value, datetime):
        return _utc_iso(value)
    raise TypeError(f"Cannot put {type(value).__name__} in an audit record.")


def _normalise(value: object) -> object:
    """Reject non-string keys (json.dumps would silently turn 1 into "1", so {1: x} and
    {"1": x} would hash the same) and turn tuples into lists."""
    if isinstance(value, dict):
        for k in value:
            if not isinstance(k, str):
                raise TypeError("Audit record keys must be strings.")
        return {k: _normalise(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_normalise(v) for v in value]
    return value


def canonical_json(record: dict) -> str:
    return json.dumps(
        _normalise(record),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=_default,
    )


def audit_hash(record: dict) -> str:
    return hashlib.sha256(canonical_json(record).encode("utf-8")).hexdigest()
