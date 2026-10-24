from common.app import Application
from common.enums import Buyer


def sample_application(estimate=None, buyer_type=Buyer.FIRST_TIME):
    return Application(
        buyer_type=buyer_type, income=95000, monthly_debts=300, deposit=60000,
        loan_amount=335000, years=30, price=395000, estimate=estimate,
    )

def backend_dict(valuation=None, buyer_type="first_time"):
    return {
        "buyerType": buyer_type,
        "financials": {
            "grossAnnualIncome": 95000,
            "monthlyDebts": 300,
            "deposit": 60000,
            "loanAmount": 335000,
            "termYears": 30,
        },
        "property": {
            "county": "Cork", "floorAreaM2": 110, "bedrooms": 3,
            "propertyType": "semi_detached", "ber": "B2", "askingPrice": 395000,
        },
        "valuation": valuation,
        "borrowerId": "uid-123",
        "brokerId": None,
    }