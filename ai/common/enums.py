from enum import StrEnum


class Buyer(StrEnum):
    FIRST_TIME = "first_time"
    SUBSEQUENT = "subsequent"


class LimitedBy(StrEnum):
    LTI = "lti"
    DEPOSIT = "deposit"