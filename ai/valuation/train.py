import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

VALUATION_DIR = Path(__file__).parent
LISTINGS_PATH = VALUATION_DIR / "data" / "listings.csv"
METRICS_PATH = VALUATION_DIR / "data" / "metrics.json"
MODEL_PATH = VALUATION_DIR / "model.joblib"

MODEL_VERSION = "gbr-1"
SEED = 11
TEST_SIZE = .2
RANGE_QUANTILES = (.1, .9)

CATEGORICAL = ["county", "propertyType", "ber"]
NUMERIC = ["floorAreaM2", "bedrooms"]
FEATURES = CATEGORICAL + NUMERIC
TARGET = "price"


def build_pipeline(seed: int = SEED) -> TransformedTargetRegressor:
    features = ColumnTransformer([
        ("categories", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
        ("numbers", "passthrough", NUMERIC),
    ])
    model = Pipeline([
        ("features", features),
        ("gbr", GradientBoostingRegressor(n_estimators=300, max_depth=3,
                                          learning_rate=.05, random_state=seed)),
    ])
    return TransformedTargetRegressor(regressor=model, func=np.log, inverse_func=np.exp)


def baseline_predict(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    county_median = train.groupby("county")[TARGET].median()
    return test["county"].map(county_median).fillna(train[TARGET].median()).to_numpy()


def train(listings: pd.DataFrame, seed: int = SEED) -> tuple[dict, dict]:
    train_df, test_df = train_test_split(listings, test_size=TEST_SIZE, random_state=seed)
    y_test = test_df[TARGET].to_numpy()

    pipeline = build_pipeline(seed).fit(train_df[FEATURES], train_df[TARGET])
    predicted = pipeline.predict(test_df[FEATURES])
    baseline = baseline_predict(train_df, test_df)

    low_ratio, high_ratio = np.quantile(y_test / predicted, RANGE_QUANTILES)
    bundle = {"pipeline": pipeline, "version": MODEL_VERSION,
              "low_ratio": float(low_ratio), "high_ratio": float(high_ratio)}

    mae_baseline = mean_absolute_error(y_test, baseline)
    mae_model = mean_absolute_error(y_test, predicted)
    metrics = {
        "modelVersion": MODEL_VERSION,
        "trainRows": len(train_df),
        "testRows": len(test_df),
        "maeBaseline": round(mae_baseline),
        "maeModel": round(mae_model),
        "improvement": round(1 - mae_model / mae_baseline, 3),
        "mapeBaseline": round(mean_absolute_percentage_error(y_test, baseline), 3),
        "mapeModel": round(mean_absolute_percentage_error(y_test, predicted), 3),
        "r2Model": round(r2_score(y_test, predicted), 3),
        "lowRatio": round(low_ratio, 3),
        "highRatio": round(high_ratio, 3),
    }
    return bundle, metrics


def predict(bundle: dict, spec: dict) -> dict:
    estimate = float(bundle["pipeline"].predict(pd.DataFrame([spec])[FEATURES])[0])
    return {
        "estimate": round(estimate, -3),
        "low": round(estimate * bundle["low_ratio"], -3),
        "high": round(estimate * bundle["high_ratio"], -3),
        "modelVersion": bundle["version"],
    }


def main() -> None:
    bundle, metrics = train(pd.read_csv(LISTINGS_PATH))
    joblib.dump(bundle, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))

    for name, value in metrics.items():
        print(f"{name:<14}{value:>12}")
    print(f"saved model to {MODEL_PATH}")


if __name__ == "__main__":
    main()