"""Request and response shapes for the API (US-311).

Python code uses snake_case; JSON and Firestore use camelCase (see docs/data-model.md).
Pydantic converts between them and rejects invalid input with a 422 error.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .lifecycle import Status

County = Literal[
    "Carlow", "Cavan", "Clare", "Cork", "Donegal", "Dublin", "Galway", "Kerry",
    "Kildare", "Kilkenny", "Laois", "Leitrim", "Limerick", "Longford", "Louth",
    "Mayo", "Meath", "Monaghan", "Offaly", "Roscommon", "Sligo", "Tipperary",
    "Waterford", "Westmeath", "Wexford", "Wicklow",
]
Ber = Literal[
    "A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3", "D1", "D2", "E1", "E2", "F", "G",
]
PropertyType = Literal["apartment", "terraced", "semi_detached", "detached", "bungalow"]
BuyerType = Literal["first_time", "subsequent"]


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid"
    )


# ---------- valuations (US-121 / US-403) ----------

class PropertySpec(ApiModel):
    county: County
    floor_area_m2: float = Field(gt=0, le=2000)
    bedrooms: int = Field(ge=0, le=10)
    property_type: PropertyType
    ber: Ber


class ValuationOut(ApiModel):
    valuation_id: str
    estimate: float
    low: float
    high: float
    model_version: str
    is_stub: bool = Field(
        description="True while the ML model (US-402/403) is not connected; numbers are fake."
    )


# ---------- applications (US-112) ----------

class Financials(ApiModel):
    gross_annual_income: float = Field(ge=0)
    monthly_debts: float = Field(ge=0)
    deposit: float = Field(ge=0)
    loan_amount: float = Field(gt=0)
    term_years: int = Field(ge=5, le=35)


class PropertyWithPrice(PropertySpec):
    asking_price: float = Field(gt=0)


class ApplicationCreate(ApiModel):
    buyer_type: BuyerType
    financials: Financials
    property: PropertyWithPrice
    valuation_id: str | None = None


class StatusChange(ApiModel):
    to: Status
    reason: str | None = Field(default=None, max_length=1000)


class HistoryOut(ApiModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    status: Status
    at: datetime
    by: str
    role: str
    reason: str | None = None


class ApplicationOut(ApiModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    id: str
    reference: str
    borrower_id: str
    borrower_name: str
    broker_id: str | None
    status: Status
    status_label: str
    status_history: list[HistoryOut]
    buyer_type: BuyerType
    financials: Financials
    property: PropertyWithPrice
    valuation: dict | None = None
    metrics: dict | None = None
    risk_tier: str | None = None
    created_at: datetime
    updated_at: datetime


class ErrorBody(ApiModel):
    code: str
    message: str
    details: list | dict | None = None


class ErrorResponse(ApiModel):
    error: ErrorBody
