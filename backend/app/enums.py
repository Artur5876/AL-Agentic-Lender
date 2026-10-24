
"""Shared string enums for the AL backend (single place for literals)"""
from enum import StrEnum


class Buyer(StrEnum):
    """Buyer category; selects the LTI limit in the calculation module (US-410, US-111)."""

    FIRST_TIME = "first_time"
    SUBSEQUENT = "subsequent"


class LimitedBy(StrEnum):
    """Which rule caps the indicative maximum loan (US-410)."""

    LTI = "lti"  # loan-to-income cap (multiple of gross income)
    DEPOSIT = "deposit"  # max loan capped by the minimum-deposit rule
