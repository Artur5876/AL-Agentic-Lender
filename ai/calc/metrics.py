from dataclasses import dataclass

from calc.config import Limits, DEFAULT_LIMITS
from common.app import Application
from common.enums import Buyer, LimitedBy


@dataclass(frozen=True)
class Metrics:
    lti: float | None
    ltv: float
    dti: float | None
    stressed_dti: float | None
    monthly_repayment: float
    lti_cap: float
    max_ltv: float
    max_dti: float

    def is_lti_ok(self) -> bool:
        return self.lti is not None and self.lti <= self.lti_cap

    def is_ltv_ok(self) -> bool:
        return self.ltv <= self.max_ltv

    def is_dti_ok(self) -> bool:
        return self.dti is not None and self.dti <= self.max_dti

    def is_stressed_dti_ok(self) -> bool:
        return self.stressed_dti is not None and self.stressed_dti <= self.max_dti

    def to_dict(self) -> dict:
        return {
            "lti": self.lti,
            "ltv": self.ltv,
            "dti": self.dti,
            "stressedDti": self.stressed_dti,
            "monthlyRepayment": self.monthly_repayment,
            "checks": {
                "ltiOk": self.is_lti_ok(),
                "ltvOk": self.is_ltv_ok(),
                "dtiOk": self.is_dti_ok(),
                "stressedDtiOk": self.is_stressed_dti_ok(),
            },
        }


class MortgageCalculator:
    def __init__(self, limits: Limits = DEFAULT_LIMITS):
        self.limits = limits

    def compute_metrics(self, app: Application, rate_shock_bps: int = 0) -> Metrics:
        value = self.property_value(app.price, app.estimate)

        rate = self.limits.base_apr + rate_shock_bps / 10_000
        repayment = self.monthly_repayment(app.loan_amount, rate, app.years)
        stressed_repayment = self.monthly_repayment(
            app.loan_amount, rate + self.limits.stress_buffer, app.years)

        return Metrics(
            lti=self.lti(app.loan_amount, app.income),
            ltv=self.ltv(app.loan_amount, value),
            dti=self.dti(app.monthly_debts, repayment, app.income),
            stressed_dti=self.dti(app.monthly_debts, stressed_repayment, app.income),
            monthly_repayment=repayment,
            lti_cap=self.lti_cap(app.buyer_type),
            max_ltv=self.limits.max_ltv,
            max_dti=self.limits.max_dti,
        )

    def lti_cap(self, buyer_type: Buyer) -> float:
        return self.limits.lti_first_time if Buyer(buyer_type) == Buyer.FIRST_TIME else self.limits.lti_subsequent

    def max_loan(self, income: float, deposit: float, buyer_type: Buyer) -> dict:
        by_income = income * self.lti_cap(buyer_type)
        by_deposit = deposit / (1 - self.limits.max_ltv) - deposit

        if by_income <= by_deposit:
            return {"maxLoan": round(by_income, 2), "limitedBy": LimitedBy.LTI}
        return {"maxLoan": round(by_deposit, 2), "limitedBy": LimitedBy.DEPOSIT}

    def price_vs_valuation(self, price: float, estimate: float) -> dict:
        difference = price - estimate
        difference_pct = difference / estimate
        return {
            "differenceEur": round(difference, 2),
            "differencePct": round(difference_pct, 4),
            "overValued": difference_pct > self.limits.overvaluation_threshold,
        }

    @staticmethod
    def monthly_repayment(principal: float, rate: float, years: int) -> float:
        n = years * 12
        r = rate / 12
        if r == 0:
            return round(principal / n, 2)
        return round(principal * r / (1 - (1 + r) ** -n), 2)

    @staticmethod
    def lti(loan_amount: float, income: float) -> float | None:
        if income == 0:
            return None
        return round(loan_amount / income, 4)

    @staticmethod
    def property_value(price: float, val_est: float | None = None) -> float:
        if val_est is None:
            return price
        return min(price, val_est)

    @staticmethod
    def ltv(loan_amount: float, value: float) -> float:
        return round(loan_amount / value, 4)

    @staticmethod
    def dti(month_debts: float, mr: float, income: float) -> float | None:
        if income == 0:
            return None
        return round((month_debts + mr) / (income / 12), 4)
