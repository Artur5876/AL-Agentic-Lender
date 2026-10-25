import pandas as pd
import pytest

from valuation.generate import MEDIANS_PATH, generate
from valuation.train import predict, train

HOUSE = {"county": "Cork", "floorAreaM2": 110, "bedrooms": 3,
         "propertyType": "semi_detached", "ber": "B2"}


@pytest.fixture(scope="module")
def trained():
    return train(generate(pd.read_csv(MEDIANS_PATH), n=2000))


def test_model_beats_baseline(trained):
    _, metrics = trained
    assert metrics["maeModel"] < metrics["maeBaseline"]


def test_prediction_has_a_range(trained):
    bundle, _ = trained
    result = predict(bundle, HOUSE)
    assert 0 < result["low"] < result["estimate"] < result["high"]
    assert result["modelVersion"] == "gbr-1"


def test_bigger_house_is_worth_more(trained):
    bundle, _ = trained
    small = predict(bundle, {**HOUSE, "floorAreaM2": 70})["estimate"]
    big = predict(bundle, {**HOUSE, "floorAreaM2": 180})["estimate"]
    assert big > small


def test_same_seed_gives_same_metrics(trained):
    _, metrics = trained
    _, again = train(generate(pd.read_csv(MEDIANS_PATH), n=2000))
    assert again == metrics


def test_unknown_category_does_not_crash(trained):
    bundle, _ = trained
    assert predict(bundle, {**HOUSE, "county": "Atlantis"})["estimate"] > 0