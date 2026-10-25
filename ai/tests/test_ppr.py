import pandas as pd
import pytest

from valuation.ppr import clean, county_medians, load_raw, parse_price
from valuation.schema import COUNTIES


def row(price="€300,000.00", county="Cork", market="No", vat="No",
        desc="Second-Hand Dwelling house /Apartment", date="02/01/2025", address="1 Main St"):
    return {"date": date, "address": address, "county": county, "eircode": "",
            "price": price, "not_full_market": market, "vat_exclusive": vat,
            "description": desc, "size_desc": ""}


def test_parse_price():
    assert parse_price("€395,000.00") == 395000.0
    assert parse_price("€281,938.33") == pytest.approx(281938.33)


@pytest.mark.parametrize("bad,rule", [
    (row(market="Yes", address="2"), "not_full_market"),
    (row(desc="New Dwelling house /Apartment", vat="Yes", address="2"), "new_dwelling"),
    (row(county="Atlantis", address="2"), "unknown_county"),
    (row(), "duplicate"),
])
def test_each_rule_removes_its_row(bad, rule):
    df, report = clean(pd.DataFrame([row(), bad]))
    assert report[rule] == 1
    assert len(df) == 1


def test_outliers_are_cut_per_county():
    prices = [f"€{p},000.00" for p in [100] + [300] * 98 + [5000]]
    df, report = clean(pd.DataFrame([row(price=p, address=str(i)) for i, p in enumerate(prices)]))
    assert report["outlier"] == 2
    assert df["price"].between(300000, 300000).all()


def test_medians_cover_every_county():
    df, _ = clean(pd.DataFrame([row(county=c, address=c) for c in COUNTIES]))
    medians = county_medians(df)
    assert list(medians["county"]) == list(COUNTIES)
    assert (medians["n_sales"] == 1).all()


def test_medians_fail_when_a_county_is_missing():
    df, _ = clean(pd.DataFrame([row()]))
    with pytest.raises(ValueError):
        county_medians(df)


def test_load_raw_reads_cp1252_and_renames(tmp_path):
    header = ("Date of Sale (dd/mm/yyyy),Address,County,Eircode,Price (€),Not Full Market Price,"
              "VAT Exclusive,Description of Property,Property Size Description\r\n")
    line = ('"02/01/2025","1 Main St","Cork","","€239,000.00","No","No",'
            '"Second-Hand Dwelling house /Apartment",""\r\n')
    path = tmp_path / "ppr.csv"
    path.write_bytes((header + line).encode("cp1252"))
    df = load_raw(path)
    assert list(df.columns)[:5] == ["date", "address", "county", "eircode", "price"]
    assert df.loc[0, "price"] == "€239,000.00"