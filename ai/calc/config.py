from dataclasses import dataclass


@dataclass(frozen=True)
class Limits:
    lti_first_time: float = 4.
    lti_subsequent: float = 3.5
    max_ltv: float = .90
    max_dti: float = .4
    base_apr: float = .04
    stress_buffer: float = .02
    overvaluation_threshold: float = .1

DEFAULT_LIMITS = Limits()