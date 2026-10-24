def monthly_repayment(principal: float, annual_rate: float, term_years: int) -> float:
    n = term_years * 12
    r = annual_rate / 12
    if r == 0:
        return round(principal / n, 2)
    return round(principal * r / (1 - (1 + r) ** -n), 2)


def lti(loan_amount: float, gross_annual_income: float) -> float | None:
    if gross_annual_income == 0:
        return None
    return round(loan_amount / gross_annual_income, 4)