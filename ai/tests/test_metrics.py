from calc.metrics import monthly_repayment


def test_repayment_standard():
    assert monthly_repayment(335000, 0.04, 30) == 1599.34


def test_repayment_zero_rate():
    assert monthly_repayment(120000, 0.0, 10) == 1000.00
