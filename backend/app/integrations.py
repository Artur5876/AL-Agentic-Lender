"""Connection points to the AI lead's code. Core calls these; the AI lead replaces the bodies.

Keeping them here means the API contract (US-311) is stable while the ML model and
calculation module are still being built.
"""

from __future__ import annotations

from calc.metrics import MortgageCalculator
from common.app import Application

STUB_MODEL_VERSION = "stub-0"
_calculator = MortgageCalculator()


def estimate_value(property_spec: dict) -> dict:
    """Placeholder for the valuation model (US-402 / US-403, AI lead).

    Returns FIXED fake numbers so the mobile property checker (US-121) can be built.
    They do not depend on the input and must never be shown as a real estimate.
    Replace with: load the trained model once, predict, return the same keys.
    """
    return {
        "estimate": 380000.0,
        "low": 360000.0,
        "high": 400000.0,
        "modelVersion": STUB_MODEL_VERSION,
    }


def compute_metrics(application: dict) -> dict:
    """Calculation module (US-410, AI lead): LTI, LTV, DTI, stressed DTI, repayment, checks."""
    return _calculator.compute_metrics(Application.from_dict(application)).to_dict()
