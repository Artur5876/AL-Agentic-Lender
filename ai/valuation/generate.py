from pathlib import Path

import numpy as np
import pandas as pd

from valuation.schema import BERS, PROPERTY_TYPES

DATA_DIR = Path(__file__).parent / "data"
MEDIANS_PATH = DATA_DIR / "county_medians.csv"
LISTINGS_PATH = DATA_DIR / "listings.csv"

SEED = 11
N_LISTINGS = 20_000

TYPE_SHARE = {"apartment": .20, "terraced": .25, "semi_detached": .30,
              "detached": .20, "bungalow": .05}
TYPE_FACTOR = {"apartment": .85, "terraced": .90, "semi_detached": 1.0,
               "detached": 1.25, "bungalow": 1.05}
BEDROOMS = {"apartment": (1, 3), "terraced": (2, 4), "semi_detached": (3, 4),
            "detached": (3, 5), "bungalow": (2, 4)}

BER_SHARE = {"A1": .01, "A2": .03, "A3": .04, "B1": .03, "B2": .05, "B3": .08,
             "C1": .10, "C2": .11, "C3": .11, "D1": .11, "D2": .10,
             "E1": .06, "E2": .05, "F": .06, "G": .06}
BER_FACTOR = {"A1": 1.12, "A2": 1.10, "A3": 1.08, "B1": 1.06, "B2": 1.05, "B3": 1.03,
              "C1": 1.01, "C2": 1.0, "C3": .99, "D1": .97, "D2": .95,
              "E1": .92, "E2": .90, "F": .87, "G": .85}

TYPICAL_AREA_M2 = 100   # a 100 m2 home sells at roughly the county median
AREA_ELASTICITY = .7    # doubling the area raises the price by about 60%, not 100%
AREA_BASE_M2, AREA_PER_BEDROOM_M2 = 20, 28
AREA_NOISE, PRICE_NOISE = .15, .15


def generate(medians: pd.DataFrame, n: int = N_LISTINGS, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    county = rng.choice(medians["county"], size=n, p=medians["n_sales"] / medians["n_sales"].sum())
    ptype = rng.choice(PROPERTY_TYPES, size=n, p=[TYPE_SHARE[t] for t in PROPERTY_TYPES])
    ber = rng.choice(BERS, size=n, p=[BER_SHARE[b] for b in BERS])

    low = np.array([BEDROOMS[t][0] for t in ptype])
    high = np.array([BEDROOMS[t][1] for t in ptype])
    bedrooms = rng.integers(low, high + 1)

    area = (AREA_BASE_M2 + AREA_PER_BEDROOM_M2 * bedrooms) * rng.normal(1, AREA_NOISE, n)
    area = np.clip(area, 30, 2000).round(1)

    median = medians.set_index("county")["median_price"].loc[county].to_numpy()
    price = (median
             * (area / TYPICAL_AREA_M2) ** AREA_ELASTICITY
             * np.array([TYPE_FACTOR[t] for t in ptype])
             * np.array([BER_FACTOR[b] for b in ber])
             * rng.lognormal(0, PRICE_NOISE, n))

    return pd.DataFrame({
        "county": county,
        "floorAreaM2": area,
        "bedrooms": bedrooms,
        "propertyType": ptype,
        "ber": ber,
        "price": price.round(-3),
    })


def main() -> None:
    listings = generate(pd.read_csv(MEDIANS_PATH))
    listings.to_csv(LISTINGS_PATH, index=False)
    print(f"saved {len(listings)} listings to {LISTINGS_PATH}")
    print(listings.groupby("propertyType")["price"].median().round(-3).to_string())


if __name__ == "__main__":
    main()