from enum import StrEnum


class Buyer(StrEnum):
    FIRST_TIME = "first_time"
    SUBSEQUENT = "subsequent"


class LimitedBy(StrEnum):
    LTI = "lti"
    DEPOSIT = "deposit"


class Agent(StrEnum):
    AFFORDABILITY = "affordability"
    VALUATION = "valuation"
    MARKET_RESEARCH = "market_research"
    UNDERWRITING_STRATEGIST = "underwriting_strategist"