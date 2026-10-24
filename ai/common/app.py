from dataclasses import dataclass

from common.enums import Buyer


@dataclass(frozen=True)
class Application:
    buyer_type: Buyer
    income: float
    monthly_debts: float
    deposit: float
    loan_amount: float
    years: int
    price: float
    estimate: float | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Application":
        fin = data["financials"]
        valuation = data.get("valuation")
        return cls(
            buyer_type=Buyer(data["buyerType"]),
            income=fin["grossAnnualIncome"],
            monthly_debts=fin["monthlyDebts"],
            deposit=fin["deposit"],
            loan_amount=fin["loanAmount"],
            years=fin["termYears"],
            price=data["property"]["askingPrice"],
            estimate=valuation["estimate"] if valuation else None,
        )