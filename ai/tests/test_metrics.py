from calc.metrics import monthly_repayment, lti


def test_repayment_standard():
    assert monthly_repayment(33_5000, 0.04, 30) == 1599.34


def test_repayment_zero_rate():
    assert monthly_repayment(12_0000, 0.0, 10) == 1000.00


def test_lti_standard():
    assert lti(33_5000, 95000) == 3.5263


def test_lti_zero_income():
    assert lti(33_5000, 0) is None