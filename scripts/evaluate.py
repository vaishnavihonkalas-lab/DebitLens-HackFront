"""Small secondary synthetic check, not an independently collected benchmark."""

import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from app.core import empty_state, import_csv, analyse

s = empty_state()
s["transactions"] = import_csv((root / "samples/heldout.csv").read_text(), [])[
    "transactions"
]
fs = analyse(s)["findings"]
# Unit: service grouping in this 2-group synthetic file. Positive = included projection.
expected = {"StreamBee": True, "WEEKEND CAFE": False}
tp = fp = fn = tn = 0
for f in fs:
    pred = f["monthly_paise"] > 0
    truth = expected[f["service"]]
    tp += int(pred and truth)
    fp += int(pred and not truth)
    fn += int(not pred and truth)
    tn += int(not pred and not truth)
print(
    json.dumps(
        {
            "scope": "2 synthetic service groups; tiny development-time check, not independent held-out evidence",
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
            "true_negative": tn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
        },
        indent=2,
    )
)
