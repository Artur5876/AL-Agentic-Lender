"""Connection points to the AI lead's code (ai/ folder). Core calls these; the AI lead owns them.

Keeping them here means the API contract (US-311) stays stable when the valuation model
(US-402/403) or the calculation module (US-410) changes.
"""

from __future__ import annotations
from functools import lru_cache

import joblib

from valuation.train import MODEL_PATH, predict
from calc.metrics import MortgageCalculator
from common.app import Application

STUB_MODEL_VERSION = "stub-0"
_calculator = MortgageCalculator()


@lru_cache(maxsize=1)
def _load_model() -> dict | None:
    """Load the trained valuation model once; None if model.joblib is missing."""
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


def estimate_value(property_spec: dict) -> dict:
    """Valuation model (US-402 / US-403, AI lead). Falls back to the stub without a model."""
    bundle = _load_model()
    if bundle is None:
        return {
            "estimate": 380000.0,
            "low": 360000.0,
            "high": 400000.0,
            "modelVersion": STUB_MODEL_VERSION,
        }
    return predict(bundle, property_spec)

def compute_metrics(application: dict) -> dict:
    """Calculation module (US-410, AI lead): LTI, LTV, DTI, stressed DTI, repayment, checks."""
    return _calculator.compute_metrics(Application.from_dict(application)).to_dict()
