import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_MODE", "sqlite")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    with TestClient(app) as c:
        yield c


def test_full_workflow(client):
    assert client.get("/api/health").json()["neo4j_connected"] is False
    assert client.post("/api/demo").json()["imported"] > 0
    d = client.get("/api/dashboard").json()
    f = next(f for f in d["findings"] if f["service"] == "StreamBee")
    assert f["changes"][0]["percent"] == 33.4
    fid = f["id"]
    body = {
        "service_status": "Supported by supplied confirmation",
        "mandate_status": "Unknown",
        "request_date": "2026-09-25",
        "effective_date": "2026-09-30",
        "note": "fictional",
    }
    assert client.put("/api/cases/" + fid, json=body).status_code == 422
    assert (
        client.post(
            "/api/evidence",
            json={
                "finding_id": fid,
                "kind": "cancellation",
                "note": "fictional confirmation",
            },
        ).status_code
        == 200
    )
    assert client.put("/api/cases/" + fid, json=body).status_code == 200
    later = client.get("/api/samples/later.csv").text
    assert client.post("/api/import", json={"text": later}).json()["imported"] == 1
    assert len(client.get("/api/dashboard").json()["alerts"]) == 1
    assert client.get("/api/export").headers["content-type"] == "application/json"
    assert "service,account" in client.get("/api/export.csv").text
    assert client.post("/api/demo").json()["duplicates"] > 0
    assert client.get("/api/graph").json()["mode"] == "sqlite"
    assert client.delete("/api/workspace").json()["deleted"]
    assert not client.get("/api/dashboard").json()["findings"]


def test_invalid_inputs(client):
    assert client.post("/api/import", json={"text": "garbage"}).status_code == 422
    assert client.put("/api/cases/missing", json={}).status_code == 404
    assert client.get("/api/samples/secret").status_code == 404
    assert (
        client.post(
            "/api/evidence", json={"finding_id": "x", "kind": "made_up", "note": "x"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/import",
            content=b"x" * 3_000_001,
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413
    )


def test_persistence(client):
    client.post("/api/demo")
    before = client.get("/api/dashboard").json()["coverage"]["count"]
    assert before > 0
    assert app.state.store.load()["transactions"]


@pytest.mark.skipif(
    not os.getenv("NEO4J_TEST_URI"),
    reason="Set NEO4J_TEST_URI for real disposable Neo4j integration test",
)
def test_real_neo4j(monkeypatch):
    monkeypatch.setenv("STORAGE_MODE", "neo4j")
    monkeypatch.setenv("NEO4J_URI", os.environ["NEO4J_TEST_URI"])
    with TestClient(app) as client:
        client.delete("/api/workspace")
        try:
            assert client.get("/api/health").json()["neo4j_connected"]
            assert client.post("/api/demo").status_code == 200
            graph = client.get("/api/graph").json()
            assert graph["mode"] == "neo4j" and graph["edges"]
            f = next(
                f
                for f in client.get("/api/dashboard").json()["findings"]
                if f["service"] == "StreamBee"
            )
            client.post(
                "/api/evidence",
                json={"finding_id": f["id"], "kind": "cancellation", "note": "demo"},
            )
            client.put(
                "/api/cases/" + f["id"],
                json={
                    "service_status": "Cancellation requested",
                    "mandate_status": "Unknown",
                    "effective_date": "2026-09-30",
                },
            )
            client.post(
                "/api/import", json={"text": client.get("/api/samples/later.csv").text}
            )
            graph = client.get("/api/graph").json()
            assert any(e["label"] == "REQUIRES_REVIEW" for e in graph["edges"])
            assert client.get("/api/graph", params={"finding_id": f["id"]}).json()[
                "nodes"
            ]
        finally:
            client.delete("/api/workspace")
