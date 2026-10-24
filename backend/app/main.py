import csv
import io
import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from .core import analyse, import_csv, parse_message, safe_csv, parse_date, MAX_BYTES
from .storage import Store
from .guides import GUIDES


@asynccontextmanager
async def lifespan(app):
    app.state.store = Store()
    try:
        yield
    finally:
        app.state.store.close()


app = FastAPI(title="DebitLens", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(","),
    allow_methods=["GET", "POST", "DELETE", "PUT"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def body_limit(request, call_next):
    # Stream counting works even when Content-Length is absent or inaccurate.
    if request.method in ("POST", "PUT"):
        chunks = []
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > 3_000_000:
                return Response("Request exceeds 3 MB", status_code=413)
            chunks.append(chunk)
        request._body = b"".join(chunks)
    try:
        return await call_next(request)
    except Exception:
        # No connection strings, credentials or uploaded text in client error messages.
        return Response(
            json.dumps(
                {
                    "detail": "Storage unavailable or operation failed. Check local server and database."
                }
            ),
            media_type="application/json",
            status_code=503,
        )


def store():
    return app.state.store


def mutate(fn):
    with store().lock:
        state = store().load()
        result = fn(state)
        store().save(state)
        return result


def event(s, kind, fid):
    s["history"].append(
        {"at": datetime.now(timezone.utc).isoformat(), "kind": kind, "finding_id": fid}
    )


def require_finding(s, fid):
    if not any(f["id"] == fid for f in analyse(s)["findings"]):
        raise HTTPException(404, "Finding not found")


class ImportBody(BaseModel):
    text: str = Field(max_length=MAX_BYTES)
    mapping: dict[str, str] | None = None


class MessageBody(BaseModel):
    text: str = Field(max_length=10000)


class EvidenceBody(BaseModel):
    finding_id: str = Field(max_length=100)
    kind: Literal["receipt", "mandate", "cancellation", "price_notice"] = "receipt"
    note: str = Field(max_length=10000)
    service: str = Field(default="", max_length=200)
    amount: str = Field(default="", max_length=100)
    effective_date: str | None = None
    mandate_reference: str = Field(default="", max_length=200)
    billing_channel: str = Field(default="", max_length=100)


class CaseBody(BaseModel):
    service_status: Literal[
        "Unknown",
        "Active",
        "Cancellation requested",
        "Cancellation reported by user",
        "Supported by supplied confirmation",
    ] = "Unknown"
    mandate_status: Literal[
        "Unknown",
        "Active according to supplied information",
        "Revocation requested",
        "Revocation reported by user",
        "Supported by supplied confirmation",
    ] = "Unknown"
    request_date: str | None = None
    effective_date: str | None = None
    note: str = Field(default="", max_length=5000)


class Correction(BaseModel):
    service: str = Field(min_length=1, max_length=200)
    billing_channel: str = Field(default="UNKNOWN", max_length=100)
    subscription_reference: str = Field(default="", max_length=100)


class Decision(BaseModel):
    decision: Literal["confirmed", "rejected", "reset"]


@app.get("/api/health")
def health():
    try:
        return {"ok": True, **store().health()}
    except Exception:
        raise HTTPException(503, "Neo4j unreachable; verify environment and startup")


@app.get("/api/dashboard")
def dashboard():
    with store().lock:
        return analyse(store().load())


@app.post("/api/import/headers")
def import_headers(body: ImportBody):
    reader = csv.reader(io.StringIO(body.text.lstrip("\ufeff")))
    return {"headers": next(reader, [])}


@app.post("/api/import/preview")
def preview(body: ImportBody):
    try:
        r = import_csv(body.text, [], body.mapping)
        return {
            "headers": r["headers"],
            "rows": r["transactions"][:8],
            "valid_count": len(r["transactions"]),
            "errors": r["errors"],
            "duplicates": r["duplicates"],
        }
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@app.post("/api/import")
def commit_import(body: ImportBody):
    def operation(s):
        try:
            r = import_csv(body.text, s["transactions"], body.mapping)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        s["transactions"].extend(r["transactions"])
        event(s, "import", "")
        return {
            "imported": len(r["transactions"]),
            "duplicates": r["duplicates"],
            "errors": r["errors"],
        }

    return mutate(operation)


@app.post("/api/messages/preview")
def message_preview(body: MessageBody):
    return parse_message(body.text)


@app.post("/api/evidence")
def evidence(body: EvidenceBody):
    def operation(s):
        require_finding(s, body.finding_id)
        e = body.model_dump()
        e["id"] = uuid.uuid4().hex
        if body.effective_date:
            try:
                e["effective_date"] = parse_date(body.effective_date)
            except ValueError as exc:
                raise HTTPException(422, str(exc))
        s["evidence"].append(e)
        event(s, "evidence added", body.finding_id)
        return e

    return mutate(operation)


@app.put("/api/cases/{fid}")
def update_case(fid: str, body: CaseBody):
    def operation(s):
        require_finding(s, fid)
        c = body.model_dump()
        for k in ("request_date", "effective_date"):
            if c[k]:
                try:
                    c[k] = parse_date(c[k])
                except ValueError as exc:
                    raise HTTPException(422, str(exc))
        if (
            c["request_date"]
            and c["effective_date"]
            and c["effective_date"] < c["request_date"]
        ):
            raise HTTPException(422, "Effective date cannot precede request date")
        if "Supported by supplied confirmation" in (
            c["service_status"],
            c["mandate_status"],
        ):
            if not any(
                e["finding_id"] == fid and e["kind"] == "cancellation"
                for e in s["evidence"]
            ):
                raise HTTPException(422, "Add cancellation confirmation evidence first")
        s["cases"][fid] = c
        event(s, "case updated", fid)
        return c

    return mutate(operation)


@app.put("/api/findings/{fid}/decision")
def decision(fid: str, body: Decision):
    def operation(s):
        require_finding(s, fid)
        if body.decision == "reset":
            s["decisions"].pop(fid, None)
        else:
            s["decisions"][fid] = body.decision
        event(s, "finding " + body.decision, fid)
        return {"ok": True}

    return mutate(operation)


@app.put("/api/transactions/{tid}")
def correct(tid: str, body: Correction):
    def operation(s):
        if not any(t["id"] == tid for t in s["transactions"]):
            raise HTTPException(404, "Transaction not found")
        s["overrides"][tid] = body.model_dump()
        event(s, "transaction corrected", tid)
        return {"ok": True}

    return mutate(operation)


@app.get("/api/guides")
def guides():
    return GUIDES


@app.get("/api/graph")
def graph(finding_id: str | None = None):
    with store().lock:
        return store().graph(finding_id)


@app.get("/api/export")
def export():
    with store().lock:
        data = {
            "scope": "local single-user prototype; supplied evidence is unverified",
            **analyse(store().load()),
        }
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="DebitLens_evidence.json"'
        },
    )


@app.get("/api/export.csv")
def export_csv():
    with store().lock:
        rows = analyse(store().load())["findings"]
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["service", "account", "label", "cycle", "monthly_INR"])
    for f in rows:
        w.writerow(
            [safe_csv(f[k] or "") for k in ("service", "account", "label", "cycle")]
            + [f["monthly_paise"] / 100]
        )
    return Response(
        out.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="DebitLens_findings.csv"'
        },
    )


@app.delete("/api/workspace")
def delete():
    with store().lock:
        store().delete()
    return {"deleted": True}


@app.get("/api/samples/{name}")
def sample_download(name: str):
    if name not in ("initial.csv", "later.csv", "message.txt", "heldout.csv"):
        raise HTTPException(404)
    return Response(
        (Path(__file__).resolve().parents[1] / "samples" / name).read_text(),
        media_type="text/plain",
    )


@app.post("/api/demo")
def load_demo():
    text = (Path(__file__).resolve().parents[1] / "samples/initial.csv").read_text()
    return commit_import(ImportBody(text=text))
