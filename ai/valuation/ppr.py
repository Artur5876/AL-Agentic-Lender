import sys
from pathlib import Path

import pandas as pd

from valuation.schema import COUNTIES

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_RAW = DATA_DIR / "raw" / "PPR-2025.csv"
MEDIANS_PATH = DATA_DIR / "county_medians.csv"

COLUMNS = {
    "Date of Sale (dd/mm/yyyy)": "date",
    "Address": "address",
    "County": "county",
    "Eircode": "eircode",
    "Price (€)": "price",
    "Not Full Market Price": "not_full_market",
    "VAT Exclusive": "vat_exclusive",
    "Description of Property": "description",
    "Property Size Description": "size_desc",
}


def load_raw(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="cp1252", dtype=str, keep_default_na=False)
    missing = set(COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"PPR file is missing columns: {sorted(missing)}")
    return df.rename(columns=COLUMNS)[list(COLUMNS.values())]


def parse_price(value: str) -> float:
    return float(value.replace("€", "").replace(",", "").strip())


def _keep(df: pd.DataFrame, mask: pd.Series, rule: str, report: dict) -> pd.DataFrame:
    report[rule] = int((~mask).sum())
    return df[mask]


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    report = {"raw": len(df)}
    df = df.copy()
    df["price"] = df["price"].map(parse_price)
    df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y")

    df = _keep(df, df["not_full_market"] == "No", "not_full_market", report)
    df = _keep(df, df["description"].str.startswith("Second-Hand")
               & (df["vat_exclusive"] == "No"), "new_dwelling", report)
    df = _keep(df, df["county"].isin(COUNTIES), "unknown_county", report)
    df = _keep(df, ~df.duplicated(subset=["date", "address", "price"]), "duplicate", report)

    prices = df.groupby("county")["price"]
    low = prices.transform(lambda s: s.quantile(0.01))
    high = prices.transform(lambda s: s.quantile(0.99))
    df = _keep(df, df["price"].between(low, high), "outlier", report)

    report["clean"] = len(df)
    return df, report


def county_medians(df: pd.DataFrame) -> pd.DataFrame:
    out = df.groupby("county")["price"].agg(median_price="median", n_sales="size")
    missing = set(COUNTIES) - set(out.index)
    if missing:
        raise ValueError(f"No sales left for counties: {sorted(missing)}")
    return out.reindex(COUNTIES).rename_axis("county").reset_index()


def main(raw_path: Path = DEFAULT_RAW) -> None:
    df, report = clean(load_raw(raw_path))
    medians = county_medians(df)
    medians.to_csv(MEDIANS_PATH, index=False)

    for rule, n in report.items():
        print(f"{rule:<16}{n:>8}")
    print(f"saved {len(medians)} counties to {MEDIANS_PATH}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_RAW)