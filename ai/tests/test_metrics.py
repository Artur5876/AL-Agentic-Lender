from calc.config import Limits
from calc.metrics import MortgageCalculator
from common.app import Application
from common.enums import Buyer, LimitedBy
from common.tests import sample_application, backend_dict

calc = MortgageCalculator()


def test_repayment_standard():
    assert calc.monthly_repayment(335_000, 0.04, 30) == 1599.34


def test_repayment_zero_rate():
    assert calc.monthly_repayment(120_000, 0.0, 10) == 1000


def test_lti_standard():
    assert calc.lti(335_000, 95_000) == 3.5263


def test_lti_zero_income():
    assert calc.lti(335_000, 0) is None


def test_property_value_takes_lower():
    assert calc.property_value(395_000, 380_000) == 380000


def test_property_value_without_estimate():
    assert calc.property_value(395_000) == 395000


def test_ltv_standard():
    assert calc.ltv(335_000, 395_000) == .8481


def test_ltv_with_valuation():
    assert calc.ltv(335_000, 380_000) == .8816


def test_dti_standard():
    assert calc.dti(300, 1599.34, 95_000) == .2399


def test_dti_no_other_debts():
    assert calc.dti(0, 1000, 60_000) == 0.2


def test_dti_zero_income():
    assert calc.dti(300, 1599.34, 0) is None


def test_max_loan_limited_by_income():
    assert calc.max_loan(95_000, 60_000, Buyer.FIRST_TIME) == {"maxLoan": 380000.0, "limitedBy": LimitedBy.LTI}


def test_max_loan_subsequent_buyer():
    assert calc.max_loan(95_000, 60_000, Buyer.SUBSEQUENT) == {"maxLoan": 332500.0, "limitedBy": LimitedBy.LTI}


def test_max_loan_limited_by_deposit():
    assert calc.max_loan(200_000, 30_000, Buyer.FIRST_TIME) == {"maxLoan": 270000.0, "limitedBy": LimitedBy.DEPOSIT}


def test_max_loan_custom_limits():
    calc = MortgageCalculator(Limits(lti_first_time=3.0))
    assert calc.max_loan(95_000, 60_000, Buyer.FIRST_TIME)["maxLoan"] == 285000.0


def test_price_vs_valuation_standard():
    assert calc.price_vs_valuation(395000, 380000) == {
        "differenceEur": 15_000., "differencePct": .0395, "overValued": False,
    }


def test_price_vs_valuation_exactly_threshold():
    assert calc.price_vs_valuation(110_000, 100_000)["overValued"] is False


def test_price_vs_valuation_above_threshold():
    assert calc.price_vs_valuation(110_100, 100_000)["overValued"] is True


def test_price_vs_valuation_below_estimate():
    result = calc.price_vs_valuation(360_000, 380_000)
    assert result["differenceEur"] == -20_000.
    assert result["overValued"] is False


def test_compute_metrics_standard():
    m = calc.compute_metrics(sample_application())
    assert m.monthly_repayment == 1599.34
    assert m.lti == 3.5263
    assert m.ltv == 0.8481
    assert m.dti == 0.2399
    assert m.stressed_dti == 0.2916
    assert m.is_lti_ok() and m.is_ltv_ok() and m.is_dti_ok() and m.is_stressed_dti_ok()


def test_subsequent_buyer_fails_lti():
    m = calc.compute_metrics(sample_application(buyer_type=Buyer.SUBSEQUENT))
    assert m.is_lti_ok() is False


def test_zero_income_fails_checks():
    app = Application(buyer_type=Buyer.FIRST_TIME, income=0, monthly_debts=0,
                      deposit=60000, loan_amount=335000, years=30, price=395000)
    m = calc.compute_metrics(app)
    assert m.lti is None
    assert m.is_lti_ok() is False


def test_to_dict_has_backend_keys():
    d = calc.compute_metrics(sample_application()).to_dict()
    assert {"lti", "ltv", "dti", "stressedDti", "monthlyRepayment", "checks"} == d.keys()


def test_from_dict_reads_every_field():
    app = Application.from_dict(backend_dict(valuation={"estimate": 380000}))
    assert app.buyer_type == Buyer.FIRST_TIME
    assert app.income == 95_000
    assert app.monthly_debts == 300
    assert app.deposit == 60_000
    assert app.loan_amount == 335_000
    assert app.years == 30
    assert app.price == 395_000
    assert app.estimate == 380_000


def test_from_dict_without_valuation():
    app = Application.from_dict(backend_dict(valuation=None))
    assert app.estimate is None


def test_from_dict_missing_valuation_key():
    data = backend_dict()
    del data["valuation"]
    assert Application.from_dict(data).estimate is None


def test_from_dict_converts_buyer_type():
    app = Application.from_dict(backend_dict(buyer_type=Buyer.SUBSEQUENT.value))
    assert app.buyer_type is Buyer.SUBSEQUENT
