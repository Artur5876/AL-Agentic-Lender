import pandas as pd
import pytest

from valuation.generate import MEDIANS_PATH, generate
from valuation.schema import BERS, COUNTIES, PROPERTY_TYPES


@pytest.fixture(scope="module")
def listings():
    return generate(pd.read_csv(MEDIANS_PATH))


def test_no_missing_values(listings):
    assert not listings.isna().any().any()


def test_values_match_the_api(listings):
    assert set(listings["county"]) == set(COUNTIES)
    assert set(listings["propertyType"]) <= set(PROPERTY_TYPES)
    assert set(listings["ber"]) <= set(BERS)
    assert listings["floorAreaM2"].between(0, 2000, inclusive="right").all()
    assert listings["bedrooms"].between(0, 10).all()
    assert (listings["price"] > 0).all()


def test_same_seed_gives_same_data():
    medians = pd.read_csv(MEDIANS_PATH)
    pd.testing.assert_frame_equal(generate(medians, n=500, seed=1),
                                  generate(medians, n=500, seed=1))


def test_prices_follow_the_assumptions(listings):
    by_type = listings.groupby("propertyType")["price"].median()
    assert by_type["detached"] > by_type["apartment"]

    by_ber = listings.groupby("ber")["price"].median()
    assert by_ber["A1"] > by_ber["G"]

    by_county = listings.groupby("county")["price"].median()
    assert by_county["Dublin"] > by_county["Donegal"]