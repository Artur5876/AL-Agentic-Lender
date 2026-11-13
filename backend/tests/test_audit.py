"""US-331: canonical serialisation + SHA-256 audit hash."""

import hashlib
from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.audit import audit_hash, canonical_json

AT = datetime(2026, 11, 13, 14, 2, 11, 123456, tzinfo=UTC)
RECORD = {  # synthetic
    "applicationId": "AL-2026-0122",
    "decision": {"outcome": "underwriter_approved", "reason": None, "by": "uw-rachel", "at": AT},
    "creditMemo": "[STUB] Passes every check.",
    "valuation": {"estimate": 380000.0, "low": 360000.0, "high": 400000.0,
                  "modelVersion": "stub-0"},
    "metrics": {"lti": 3.5263, "ltv": 0.8481, "checks": {"ltiOk": True, "ltvOk": True}},
}


def _reordered(d):
    """Same content, keys inserted in reverse order at every level."""
    if isinstance(d, dict):
        return {k: _reordered(d[k]) for k in reversed(list(d))}
    return d


def test_same_record_same_hash():
    assert audit_hash(RECORD) == audit_hash(dict(RECORD))
    assert len(audit_hash(RECORD)) == 64 and int(audit_hash(RECORD), 16) >= 0


def test_key_order_does_not_matter_at_any_level():
    shuffled = _reordered(RECORD)
    assert list(shuffled) != list(RECORD)
    assert list(shuffled["decision"]) != list(RECORD["decision"])
    assert canonical_json(shuffled) == canonical_json(RECORD)
    assert audit_hash(shuffled) == audit_hash(RECORD)


@pytest.mark.parametrize("change", [
    lambda r: r.update(applicationId="AL-2026-0123"),
    lambda r: r.update(creditMemo=r["creditMemo"] + " "),
    lambda r: r["decision"].update(outcome="declined"),
    lambda r: r["decision"].update(at=AT + timedelta(microseconds=1)),
    lambda r: r["valuation"].update(estimate=380000.01),
    lambda r: r["metrics"]["checks"].update(ltvOk=False),       # nested 2 levels deep
    lambda r: r["metrics"].pop("lti"),
    lambda r: r.update(extra=None),
], ids=["top", "memo_whitespace", "nested", "time_1us", "number", "deep_nested",
        "removed_key", "added_key"])
def test_one_changed_field_gives_a_different_hash(change):
    import copy
    changed = copy.deepcopy(RECORD)
    change(changed)
    assert audit_hash(changed) != audit_hash(RECORD)


def test_canonical_form_is_exact():
    rec = {"b": 1, "a": {"y": [1, 2, {"z": True}], "x": None}, "é": "café", "t": AT}
    assert canonical_json(rec) == (
        '{"a":{"x":null,"y":[1,2,{"z":true}]},"b":1,'
        '"t":"2026-11-13T14:02:11.123456+00:00","é":"café"}'
    )
    expected = hashlib.sha256(canonical_json(rec).encode("utf-8")).hexdigest()
    assert audit_hash(rec) == expected


def test_datetimes_are_written_in_utc():
    dublin_summer = timezone(timedelta(hours=1))
    same_instant = AT.astimezone(dublin_summer)
    assert canonical_json({"t": same_instant}) == canonical_json({"t": AT})
    assert '"2026-11-13T14:02:11.123456+00:00"' in canonical_json({"t": same_instant})


def test_firestore_timestamp_subclass_hashes_like_plain_datetime():
    from google.api_core.datetime_helpers import DatetimeWithNanoseconds
    fs_time = DatetimeWithNanoseconds(2026, 11, 13, 14, 2, 11, 123456, tzinfo=UTC)
    assert canonical_json({"t": fs_time}) == canonical_json({"t": AT})


def test_tuple_and_list_are_the_same():
    assert audit_hash({"a": (1, 2)}) == audit_hash({"a": [1, 2]})


@pytest.mark.parametrize("bad", [
    {"t": datetime(2026, 11, 13, 14, 0)},          # naive datetime: ambiguous
    {"x": float("nan")},
    {"x": float("inf")},
    {"x": {1, 2}},                                 # set: no stable order
    {1: "int key"},                                # would collide with "1"
    {"nested": {2: "x"}},
])
def test_ambiguous_values_are_rejected(bad):
    with pytest.raises((TypeError, ValueError)):
        canonical_json(bad)
