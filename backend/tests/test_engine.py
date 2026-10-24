import csv
import io
from datetime import date
import pytest
from app.core import (
    import_csv,
    analyse,
    empty_state,
    paise,
    cadence,
    parse_date,
    parse_message,
    safe_csv,
)


def csv_text(rows, ids=True):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(
        [
            "transaction_id",
            "date",
            "description",
            "amount",
            "direction",
            "account_label",
            "currency",
            "payment_rail",
            "mandate_reference",
            "subscription_reference",
            "billing_channel",
        ]
    )
    for i, r in enumerate(rows):
        d, desc, amount, *extra = r
        w.writerow(
            [
                str(i) if ids else "",
                d,
                desc,
                amount,
                extra[0] if extra else "debit",
                "bank",
                "INR",
                "CARD",
                "",
                "",
                "DIRECT",
            ]
        )
    return out.getvalue()


def state(rows):
    s = empty_state()
    s["transactions"] = import_csv(csv_text(rows), [])["transactions"]
    return s


def rows(desc="STREAMBEE", amounts=("299", "299", "399")):
    return [(f"2026-{m}-05", desc, a) for m, a in zip(["07", "08", "09"], amounts)]


@pytest.mark.parametrize(
    "value", ["0", "-1", "NaN", "Infinity", "1.001", "100000001", "abc"]
)
def test_bad_money(value):
    with pytest.raises(ValueError):
        paise(value)


def test_integer_money():
    assert paise("299.99") == 29999


def test_date():
    assert parse_date("31/01/2026") == "2026-01-31"
    with pytest.raises(ValueError):
        parse_date("01-31-26")


def test_price():
    f = analyse(state(rows()))["findings"][0]
    assert f["changes"][0]["percent"] == 33.4
    assert f["changes"][0]["difference"] == 10000
    assert f["label"] == "Likely recurring"


def test_discretionary_not_projected():
    f = analyse(state(rows("GROCER")))["findings"][0]
    assert f["label"] == "Possible recurring; review needed"
    assert f["monthly_paise"] == 0
    assert not f["changes"]


def test_processor_ambiguous():
    f = analyse(state(rows("RAZORPAY")))["findings"][0]
    assert f["category"] == "ambiguous" and f["monthly_paise"] == 0 and not f["changes"]


def test_month_end():
    assert (
        cadence([date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]) == "monthly"
    )


def test_quarter_annual():
    assert cadence([date(2025, 1, 31), date(2025, 4, 30)]) == "quarterly"
    assert cadence([date(2024, 2, 29), date(2025, 2, 28)]) == "annual"


def test_single_annual_unknown():
    assert (
        analyse(state([("2026-01-01", "STREAMBEE", "1000")]))["findings"][0]["cycle"]
        is None
    )


def test_duplicate_and_identical_purchase():
    text = csv_text(
        [("2026-01-01", "Shop", "100"), ("2026-01-01", "Shop", "100")], False
    )
    r = import_csv(text, [])
    assert len(r["transactions"]) == 2
    r2 = import_csv(text, r["transactions"])
    assert r2["duplicates"] == 2 and not r2["transactions"]


def test_id_conflict():
    text = csv_text([("2026-01-01", "Shop", "100")])
    prior = import_csv(text, [])["transactions"]
    r = import_csv(text.replace(",100,", ",200,"), prior)
    assert len(r["errors"]) == 1


def test_validation_rows():
    text = csv_text(rows()).replace("INR", "USD", 1)
    r = import_csv(text, [])
    assert len(r["errors"]) == 1 and len(r["transactions"]) == 2


def test_mapping():
    text = csv_text(rows()).replace("description", "Details")
    assert len(import_csv(text, [], {"description": "Details"})["transactions"]) == 3


def test_refund():
    s = state(rows() + [("2026-09-06", "STREAMBEE", "399", "credit")])
    f = analyse(s)["findings"][0]
    assert f["refund_ids"] and not f["changes"]


def test_cancellation_alert_and_credit():
    s = state(
        rows()
        + [
            ("2026-10-05", "STREAMBEE", "399"),
            ("2026-10-06", "STREAMBEE", "50", "credit"),
        ]
    )
    fid = analyse(s)["findings"][0]["id"]
    s["cases"][fid] = {
        "service_status": "Cancellation reported by user",
        "mandate_status": "Unknown",
        "effective_date": "2026-09-30",
        "request_date": "2026-09-20",
        "note": "demo",
    }
    result = analyse(s)
    assert (
        len(result["alerts"]) == 1
        and result["alerts"][0]["transaction"]["direction"] == "debit"
    )


def test_effective_not_request_date():
    s = state(rows())
    fid = analyse(s)["findings"][0]["id"]
    s["cases"][fid] = {
        "service_status": "Cancellation requested",
        "effective_date": "2026-09-30",
        "request_date": "2026-08-01",
    }
    assert not analyse(s)["alerts"]


def test_rejection_excludes_projection():
    s = state(rows())
    fid = analyse(s)["findings"][0]["id"]
    s["decisions"][fid] = "rejected"
    assert analyse(s)["monthly_paise"] == 0


def test_correction_split():
    s = state(rows())
    s["overrides"][s["transactions"][0]["id"]] = {
        "service": "Other",
        "billing_channel": "DIRECT",
        "subscription_reference": "2",
    }
    assert len(analyse(s)["findings"]) == 2


def test_separate_references():
    s = state(rows() + [("2026-09-15", "STREAMBEE", "599")])
    s["transactions"][-1]["subscription_reference"] = "other"
    assert len(analyse(s)["findings"]) == 2


def test_messages():
    assert (
        parse_message("Kind: cancellation\nEffective date: 2026-09-30")[
            "effective_date"
        ]
        == "2026-09-30"
    )


def test_formula_export():
    assert safe_csv(" =SUM(A1)") == "' =SUM(A1)"
