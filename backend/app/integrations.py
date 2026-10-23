"""Connection points to the AI lead's code. Core calls these; the AI lead replaces the bodies.

Keeping them here means the API contract (US-311) is stable while the ML model and
calculation module are still being built.
"""

from __future__ import annotations

STUB_MODEL_VERSION = "stub-0"


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


def compute_metrics(application: dict) -> dict | None:
    """Placeholder for the calculation module (US-410, AI lead).

    Must return {"lti", "ltv", "dti", "stressedDti", "monthlyRepayment"} computed by
    tested Python code. Returns None until US-410 is connected, so the clients show "—".
    Core does not calculate these itself, so there is exactly one source of the numbers.
    """
    return None
