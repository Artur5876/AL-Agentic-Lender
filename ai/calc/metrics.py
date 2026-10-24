def monthly_repayment(principal: float, annual_rate: float, term_years: int) -> float:
    n = term_years * 12
    r = annual_rate / 12
    if r == 0:
        return round(principal / n, 2)
    return round(principal * r / (1 - (1 + r) ** -n), 2)