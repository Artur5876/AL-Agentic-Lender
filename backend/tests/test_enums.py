"""Unit tests for the shared string enums (must match ai/common/enums.py)."""

import json

import pytest

from app.enums import Buyer, LimitedBy


@pytest.mark.parametrize(
    ("member", "value"),
    [
        (Buyer.FIRST_TIME, "first_time"),
        (Buyer.SUBSEQUENT, "subsequent"),
        (LimitedBy.LTI, "lti"),
        (LimitedBy.DEPOSIT, "deposit"),
    ],
)
def test_member_equals_string_value(member, value):
    assert member == value
    assert member.value == value
    assert str(member) == value


def test_json_dumps_uses_plain_strings():
    payload = {"buyerType": Buyer.FIRST_TIME, "limitedBy": LimitedBy.DEPOSIT}
    assert json.dumps(payload) == '{"buyerType": "first_time", "limitedBy": "deposit"}'


def test_parse_from_string():
    assert Buyer("first_time") is Buyer.FIRST_TIME
    assert LimitedBy("deposit") is LimitedBy.DEPOSIT


@pytest.mark.parametrize(("enum", "value"), [(Buyer, "second_time"), (LimitedBy, "ltv")])
def test_unknown_value_raises(enum, value):
    with pytest.raises(ValueError):
        enum(value)
