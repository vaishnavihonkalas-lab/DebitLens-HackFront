"""Deterministic payment analysis. All amounts are integer paise."""

import calendar
import csv
import hashlib
import io
import re
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

ALIASES = {
    "STREAMBEE": ("StreamBee", "subscription"),
    "SBEE MEDIA": ("StreamBee", "subscription"),
    "CLOUDNEST": ("CloudNest", "subscription"),
    "LEARNLOOP": ("LearnLoop", "subscription"),
    "CITY POWER": ("City Power", "utility"),
}
PROCESSORS = ("RAZORPAY", "PAYU", "CASHFREE", "BILLDESK", "GOOGLE", "APPLE")
REQUIRED = ["date", "description", "amount", "direction", "account_label", "currency"]
MAX_BYTES = 2_000_000
MAX_ROWS = 10_000


def parse_date(value):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date().isoformat()
        except (ValueError, AttributeError):
            pass
    raise ValueError("Date must be YYYY-MM-DD or DD/MM/YYYY")


def paise(value):
    try:
        n = Decimal(str(value))
        if (
            not n.is_finite()
            or n <= 0
            or n > Decimal("100000000")
            or n.as_tuple().exponent < -2
        ):
            raise ValueError(
                "Amount must be positive with at most 2 decimals, maximum 100000000 INR"
            )
        return int(n * 100)
    except InvalidOperation as exc:
        raise ValueError("Invalid amount") from exc


def import_csv(text, existing, mapping=None):
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError("CSV exceeds 2 MB limit")
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    headers = reader.fieldnames or []
    mapping = mapping or {k: k for k in headers}
    missing = [k for k in REQUIRED if mapping.get(k, k) not in headers]
    if missing:
        raise ValueError("Missing columns: " + ", ".join(missing))
    known = {t["id"]: t for t in existing}
    # Occurrence number preserves identical purchases within one export. Without IDs,
    # cross-export matching remains heuristic and is disclosed to users.
    occurrences = defaultdict(int)
    additions, errors, duplicates = [], [], 0
    for line, row in enumerate(reader, 2):
        if line > MAX_ROWS + 1:
            raise ValueError("CSV exceeds 10000 row limit; no changes saved")

        def get(k, default=""):
            v = row.get(mapping.get(k, k), default)
            return str(v or "").strip()

        try:
            if None in row:
                raise ValueError("Extra cells: quote descriptions containing commas")
            t = {
                k: get(k)
                for k in [
                    "description",
                    "account_label",
                    "merchant_reference",
                    "mandate_reference",
                    "billing_channel",
                    "subscription_reference",
                ]
            }
            if not t["description"] or not t["account_label"]:
                raise ValueError("Description and account label are required")
            if any(len(v) > 500 for v in t.values()):
                raise ValueError("A field exceeds 500 characters")
            t.update(
                date=parse_date(get("date")),
                amount=paise(get("amount")),
                direction=get("direction").lower(),
                currency=get("currency").upper(),
                payment_rail=get("payment_rail", "UNKNOWN").upper(),
            )
            if t["currency"] != "INR":
                raise ValueError("Only INR supported")
            if t["direction"] not in ("debit", "credit"):
                raise ValueError("Direction must be debit or credit")
            if t["payment_rail"] not in ("UPI", "CARD", "NACH", "OTHER", "UNKNOWN"):
                raise ValueError("Unsupported payment rail")
            fingerprint = hashlib.sha256(
                "|".join(str(t[k]) for k in sorted(t)).encode()
            ).hexdigest()
            occurrences[fingerprint] += 1
            txid = get("transaction_id")
            t["id"] = hashlib.sha256(
                (
                    t["account_label"]
                    + "|"
                    + (txid or fingerprint + "|" + str(occurrences[fingerprint]))
                ).encode()
            ).hexdigest()[:24]
            t["source_id"] = txid
            if t["id"] in known:
                prior = known[t["id"]]
                if any(
                    prior.get(k) != t.get(k)
                    for k in ["date", "amount", "direction", "description"]
                ):
                    raise ValueError(
                        "Transaction ID conflicts with a previously imported row"
                    )
                duplicates += 1
            else:
                known[t["id"]] = t
                additions.append(t)
        except ValueError as exc:
            errors.append({"row": line, "message": str(exc)})
    return {
        "transactions": additions,
        "errors": errors,
        "duplicates": duplicates,
        "headers": headers,
    }


def identity(t):
    desc = t["description"].upper()
    for alias, (service, category) in ALIASES.items():
        if alias in desc:
            return service, category, "Fictional demo alias registry: " + alias
    if any(p in desc for p in PROCESSORS):
        # Unknown processor transactions cannot be confidently merged by processor name.
        service = "Unresolved: " + t["description"]
        return (
            service,
            "ambiguous",
            "Processor descriptor alone cannot establish service identity",
        )
    return (
        t["description"].strip(),
        "unknown",
        "Exact descriptor only; service unverified",
    )


def cadence(ds):
    if len(ds) < 2:
        return None
    gaps = [(b - a).days for a, b in zip(ds, ds[1:])]
    # Month arithmetic handles February, leap years and month-end billing.
    for name, months in [("monthly", 1), ("quarterly", 3), ("annual", 12)]:
        matches = []
        for a, b in zip(ds, ds[1:]):
            index = a.year * 12 + a.month - 1 + months
            y, m = divmod(index, 12)
            expected = date(y, m + 1, min(a.day, calendar.monthrange(y, m + 1)[1]))
            matches.append(abs((b - expected).days) <= (5 if months < 12 else 10))
        if all(matches):
            return name
    return None


def analyse(state):
    groups = defaultdict(list)
    for t in state["transactions"]:
        service, cat, basis = identity(t)
        override = state.get("overrides", {}).get(t["id"], {})
        service = override.get("service") or service
        channel = (
            override.get("billing_channel") or t.get("billing_channel") or "UNKNOWN"
        )
        split = (
            override.get("subscription_reference")
            or t.get("subscription_reference")
            or t.get("mandate_reference")
            or ""
        )
        # Account/channel/reference isolation avoids mixing distinct known subscriptions.
        key = (t["account_label"], service, channel, split)
        groups[key].append((t, cat, basis))
    findings, alerts = [], []
    for key, entries in groups.items():
        account, service, channel, ref = key
        fid = hashlib.sha256("|".join(key).encode()).hexdigest()[:20]
        debits = sorted(
            [t for t, _, _ in entries if t["direction"] == "debit"],
            key=lambda t: (t["date"], t["id"]),
        )
        credits = [t for t, _, _ in entries if t["direction"] == "credit"]
        refunded = set()
        # Match one credit to one earlier equal debit, within 45 days; a heuristic.
        for c in credits:
            candidates = [
                t
                for t in debits
                if t["id"] not in refunded
                and t["amount"] == c["amount"]
                and 0
                <= (date.fromisoformat(c["date"]) - date.fromisoformat(t["date"])).days
                <= 45
            ]
            if candidates:
                refunded.add(candidates[-1]["id"])
        active = [t for t in debits if t["id"] not in refunded]
        if not active:
            continue
        ds = [date.fromisoformat(t["date"]) for t in active]
        cycle = cadence(ds)
        cat = entries[0][1]
        evidence = [e for e in state["evidence"] if e.get("finding_id") == fid]
        explicit = any(t.get("mandate_reference") for t in active) or any(
            e.get("kind") == "mandate" for e in evidence
        )
        label = "Insufficient evidence"
        if explicit:
            label = "Mandate information supplied; status unverified"
        elif cycle and len(active) >= 3 and cat == "subscription":
            label = "Likely recurring"
        elif cycle:
            label = "Possible recurring; review needed"
        if cycle and cat == "utility":
            label = "Possible variable recurring bill"
        decision = state.get("decisions", {}).get(fid)
        if decision == "rejected":
            label = "Rejected by user"
        if decision == "confirmed":
            label = "Recurring pattern confirmed by user"
        amounts = [t["amount"] for t in active]
        changes = []
        # Compare same grouping and established cadence only, not unrelated purchases.
        if (
            cycle
            and cat != "ambiguous"
            and decision != "rejected"
            and (
                cat in ("subscription", "utility")
                or explicit
                or decision == "confirmed"
            )
        ):
            for old, new in zip(active, active[1:]):
                if new["amount"] > old["amount"]:
                    changes.append(
                        {
                            "old": old["amount"],
                            "new": new["amount"],
                            "difference": new["amount"] - old["amount"],
                            "percent": round(
                                100 * (new["amount"] - old["amount"]) / old["amount"], 1
                            ),
                            "date": new["date"],
                            "old_id": old["id"],
                            "new_id": new["id"],
                            "label": (
                                "Possible amount increase"
                                if cat == "utility"
                                else "Possible price increase"
                            ),
                            "notice": (
                                "Notice evidence supplied; check comparability"
                                if any(
                                    e.get("kind") == "price_notice" for e in evidence
                                )
                                else "No price-change notice found in the records you supplied."
                            ),
                        }
                    )
        included = bool(
            cycle
            and cat != "ambiguous"
            and decision != "rejected"
            and (
                cat in ("subscription", "utility")
                or explicit
                or decision == "confirmed"
            )
        )
        monthly = (
            round(
                amounts[-1] / {"monthly": 1, "quarterly": 3, "annual": 12}.get(cycle, 1)
            )
            if included
            else 0
        )
        nextdate = None
        if cycle:
            months = {"monthly": 1, "quarterly": 3, "annual": 12}[cycle]
            idx = ds[-1].year * 12 + ds[-1].month - 1 + months
            y, m = divmod(idx, 12)
            nextdate = date(
                y, m + 1, min(ds[-1].day, calendar.monthrange(y, m + 1)[1])
            ).isoformat()
        f = {
            "id": fid,
            "account": account,
            "service": service,
            "category": cat,
            "channel": channel,
            "reference": ref,
            "label": label,
            "cycle": cycle,
            "monthly_paise": monthly,
            "next_date": nextdate,
            "transactions": debits,
            "refund_ids": list(refunded),
            "evidence": evidence,
            "changes": changes,
            "reasons": [
                entries[0][2],
                f"{len(active)} non-refunded debits",
                f'Cadence: {cycle or "not established"}',
            ],
            "missing": [
                "Active mandate status is not verified",
                "Records may omit accounts or annual renewals",
            ],
        }
        findings.append(f)
        case = state["cases"].get(fid)
        if case and case.get("service_status") != "Unknown":
            cutoff = case.get("effective_date")
            for t in debits:
                if t["id"] in refunded:
                    continue
                if cutoff and t["date"] > cutoff:
                    alerts.append(
                        {
                            "finding_id": fid,
                            "service": service,
                            "transaction": t,
                            "case": case,
                            "message": "Matching debit after recorded effective cancellation date. Review required.",
                        }
                    )
                elif (
                    not cutoff
                    and case.get("request_date")
                    and t["date"] > case["request_date"]
                ):
                    alerts.append(
                        {
                            "finding_id": fid,
                            "service": service,
                            "transaction": t,
                            "case": case,
                            "message": "Debit after request; effective cancellation date unknown. Review required.",
                        }
                    )
    txs = state["transactions"]
    return {
        "findings": sorted(findings, key=lambda f: f["service"]),
        "alerts": alerts,
        "monthly_paise": sum(f["monthly_paise"] for f in findings),
        "coverage": {
            "count": len(txs),
            "accounts": sorted({t["account_label"] for t in txs}),
            "start": min((t["date"] for t in txs), default=None),
            "end": max((t["date"] for t in txs), default=None),
        },
        "cases": state["cases"],
        "history": state["history"],
    }


def parse_message(text):
    # A deliberately documented grammar makes parsing predictable, not magical NLP.
    result = {
        "raw": text,
        "kind": "receipt",
        "service": "",
        "amount": "",
        "effective_date": "",
        "mandate_reference": "",
        "billing_channel": "",
    }
    for line in text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip().lower().replace(" ", "_")
            if k in result and k != "raw":
                result[k] = v.strip()
    return result


def safe_csv(value):
    s = str(value)
    return "'" + s if s.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else s


def empty_state():
    return {
        "transactions": [],
        "evidence": [],
        "cases": {},
        "history": [],
        "overrides": {},
        "decisions": {},
    }
