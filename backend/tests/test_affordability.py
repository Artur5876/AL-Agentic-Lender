"""US-111: POST /affordability, a borrowing estimate from the calculation module (US-410)."""

import pytest
from calc.metrics import MortgageCalculator
from fastapi.testclient import TestClient

from app.chain import FakeChain
from app.config import Settings
from app.main import create_app
from app.repository import InMemoryRepository

BORROWER = {"Authorization": "Bearer dev:borrower-aoife:borrower"}
BODY = {"buyerType": "first_time", "grossAnnualIncome": 95000, "monthlyDebts": 300,
        "deposit": 60000, "termYears": 30}
CALC = MortgageCalculator()


@pytest.fixture
def repo():
    return InMemoryRepository()


@pytest.fixture
def client(repo):
    settings = Settings(repository="memory", auth_mode="dev", borrower_ref_salt="test-salt")
    return TestClient(create_app(settings, repo, chain=FakeChain()))


def estimate(client, **changes):
    return client.post("/affordability", json={**BODY, **changes}, headers=BORROWER)


# ---------- figures ----------

def test_income_limited_figures(client):
    """95,000 x 4 (first-time LTI cap) = 380,000 < deposit cap 60,000/0.10 - 60,000 = 540,000."""
    r = estimate(client)
    assert r.status_code == 200
    body = r.json()
    assert body["maxLoan"] == 380000.0 and body["limitedBy"] == "lti"
    assert body["lti"] == 4.0
    assert body["ltv"] == 0.8636  # 380,000 / 440,000, rounded by the calc module
    assert body["monthlyRepayment"] == CALC.monthly_repayment(380000.0, 0.04, 30)
    assert body["dti"] == CALC.dti(300, body["monthlyRepayment"], 95000)
    assert body["indicativeOnly"] is True
    assert set(body) == {"maxLoan", "limitedBy", "lti", "ltv", "monthlyRepayment", "dti",
                         "indicativeOnly"}


def test_deposit_limited_figures(client):
    """200,000 x 4 = 800,000 > deposit cap 30,000/0.10 - 30,000 = 270,000."""
    body = estimate(client, grossAnnualIncome=200000, deposit=30000).json()
    assert body["maxLoan"] == 270000.0 and body["limitedBy"] == "deposit"
    assert body["ltv"] == 0.9  # exactly the 90% LTV limit
    assert body["lti"] == 1.35


def test_subsequent_buyer_has_lower_cap(client):
    body = estimate(client, buyerType="subsequent", grossAnnualIncome=100000).json()
    assert body["maxLoan"] == 350000.0 and body["limitedBy"] == "lti"  # 3.5 x income


def test_longer_term_lowers_repayment_not_max_loan(client):
    short, long_ = estimate(client, termYears=20).json(), estimate(client, termYears=35).json()
    assert short["maxLoan"] == long_["maxLoan"]
    assert short["monthlyRepayment"] > long_["monthlyRepayment"]


def test_debts_change_dti_only(client):
    low, high = estimate(client, monthlyDebts=0).json(), estimate(client, monthlyDebts=900).json()
    assert low["maxLoan"] == high["maxLoan"]
    assert high["dti"] > low["dti"]


def test_zero_income(client):
    body = estimate(client, grossAnnualIncome=0).json()
    assert body["maxLoan"] == 0.0 and body["limitedBy"] == "lti"
    assert body["lti"] is None and body["dti"] is None
    assert body["ltv"] == 0.0 and body["monthlyRepayment"] == 0.0


def test_zero_income_and_deposit_does_not_crash(client):
    r = estimate(client, grossAnnualIncome=0, deposit=0)
    assert r.status_code == 200 and r.json()["ltv"] is None


def test_matches_calc_module_for_many_inputs(client):
    for income, deposit, buyer, term in [(50000, 10000, "first_time", 25),
                                         (120000, 80000, "subsequent", 35),
                                         (75000.5, 15000.25, "first_time", 5)]:
        body = estimate(client, grossAnnualIncome=income, deposit=deposit, buyerType=buyer,
                        termYears=term).json()
        expected = CALC.max_loan(income, deposit, buyer)
        assert body["maxLoan"] == expected["maxLoan"]
        assert body["limitedBy"] == expected["limitedBy"]
        assert body["lti"] == CALC.lti(expected["maxLoan"], income)
        assert body["ltv"] == CALC.ltv(expected["maxLoan"], expected["maxLoan"] + deposit)


def test_saves_nothing(client, repo):
    estimate(client)
    assert repo._apps == {} and repo._valuations == {}


# ---------- validation: 422 in the standard error format ----------

@pytest.mark.parametrize("field,value", [
    ("grossAnnualIncome", -1), ("monthlyDebts", -0.01), ("deposit", -100),
    ("termYears", 4), ("termYears", 36), ("termYears", 30.5),
    ("buyerType", "investor"), ("grossAnnualIncome", "lots"),
])
def test_bad_input_is_422(client, field, value):
    r = estimate(client, **{field: value})
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "validation_error"
    assert any(d["field"] == field for d in err["details"])


@pytest.mark.parametrize("field", list(BODY))
def test_missing_field_is_422(client, field):
    body = {k: v for k, v in BODY.items() if k != field}
    r = client.post("/affordability", json=body, headers=BORROWER)
    assert r.status_code == 422
    assert any(d["field"] == field for d in r.json()["error"]["details"])


def test_unknown_field_is_422(client):
    assert estimate(client, loanAmount=500000).status_code == 422


@pytest.mark.parametrize("term", [5, 35])
def test_term_limits_are_inclusive(client, term):
    assert estimate(client, termYears=term).status_code == 200
