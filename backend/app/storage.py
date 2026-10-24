"""Single-user prototype storage. Neo4j is default; SQLite is explicit preview mode."""

import json
import os
import sqlite3
import threading
from pathlib import Path
from .core import empty_state


class Store:
    def __init__(self):
        self.mode = os.getenv("STORAGE_MODE", "neo4j")
        self.lock = threading.RLock()
        self.driver = None
        if self.mode == "sqlite":
            path = os.getenv("SQLITE_PATH", "data/debitlens.db")
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(path, check_same_thread=False)
            self.db.execute(
                "CREATE TABLE IF NOT EXISTS workspace (id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            self.db.commit()
        elif self.mode == "neo4j":
            from neo4j import GraphDatabase

            self.driver = GraphDatabase.driver(
                os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                auth=(os.getenv("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
                connection_timeout=5,
            )
            self.driver.execute_query(
                "CREATE CONSTRAINT workspace_id IF NOT EXISTS FOR (w:Workspace) REQUIRE w.id IS UNIQUE"
            )
            self.driver.execute_query(
                "CREATE CONSTRAINT record_identity IF NOT EXISTS FOR (n:DLRecord) REQUIRE (n.workspace,n.kind,n.key) IS UNIQUE"
            )
            self.driver.execute_query(
                "CREATE INDEX record_workspace IF NOT EXISTS FOR (n:DLRecord) ON (n.workspace)"
            )
        else:
            raise ValueError("STORAGE_MODE must be neo4j or sqlite")

    def health(self):
        if self.driver:
            self.driver.verify_connectivity()
        return {
            "storage": self.mode,
            "neo4j_connected": bool(self.driver),
            "local_single_user": True,
        }

    def load(self):
        if self.driver:
            records, _, _ = self.driver.execute_query(
                "MATCH (w:Workspace {id:$id}) RETURN w.payload AS payload", id="local"
            )
            return json.loads(records[0]["payload"]) if records else empty_state()
        row = self.db.execute(
            "SELECT payload FROM workspace WHERE id=?", ("local",)
        ).fetchone()
        return json.loads(row[0]) if row else empty_state()

    def save(self, state):
        payload = json.dumps(state, ensure_ascii=False)
        if not self.driver:
            self.db.execute(
                "INSERT OR REPLACE INTO workspace VALUES (?,?)", ("local", payload)
            )
            self.db.commit()
            return
        from .core import analyse

        result = analyse(state)

        def write(tx):
            tx.run(
                "MERGE (w:Workspace {id:$id}) SET w.payload=$payload",
                id="local",
                payload=payload,
            ).consume()
            # Full projection rebuild is appropriate for bounded local prototype datasets.
            tx.run(
                "MATCH (n:DLRecord {workspace:$w}) DETACH DELETE n", w="local"
            ).consume()
            rows = []
            for f in result["findings"]:
                for t in f["transactions"]:
                    rows.append(
                        {
                            "tid": t["id"],
                            "date": t["date"],
                            "amount": t["amount"],
                            "descriptor": t["description"],
                            "account": t["account_label"],
                            "fid": f["id"],
                            "service": f["service"],
                            "channel": f["channel"],
                            "basis": f["reasons"][0],
                            "mandate": t.get("mandate_reference", ""),
                        }
                    )
            tx.run(
                """UNWIND $rows AS r
            MERGE (a:DLRecord:Account {workspace:$w,kind:'Account', key:r.account})
            MERGE (t:DLRecord:Transaction {workspace:$w,kind:'Transaction', key:r.tid}) SET t.date=r.date,t.amount=r.amount
            MERGE (d:DLRecord:MerchantDescriptor {workspace:$w,kind:'MerchantDescriptor', key:r.descriptor})
            MERGE (s:DLRecord:Service {workspace:$w,kind:'Service', key:r.fid}) SET s.name=r.service,s.basis=r.basis
            MERGE (b:DLRecord:BillingChannel {workspace:$w,kind:'BillingChannel', key:r.channel})
            MERGE (a)-[:HAS_TRANSACTION]->(t) MERGE (t)-[:DESCRIBED_AS]->(d)
            MERGE (t)-[:ATTRIBUTED_TO]->(s) MERGE (s)-[:BILLED_THROUGH]->(b)
            FOREACH (_ IN CASE WHEN r.mandate <> '' THEN [1] ELSE [] END |
                MERGE (m:DLRecord:Mandate {workspace:$w,kind:'Mandate',key:r.mandate})
                MERGE (t)-[:REFERENCES]->(m))""",
                rows=rows,
                w="local",
            ).consume()
            tx.run(
                """UNWIND $rows AS r MATCH (s:Service:DLRecord {workspace:$w,kind:'Service',key:r.finding_id})
            MERGE (e:DLRecord:Evidence {workspace:$w,kind:'Evidence',key:r.id}) SET e.kind=r.kind,e.note=r.note
            MERGE (s)-[:SUPPORTED_BY]->(e)""",
                rows=[
                    {
                        "id": e["id"],
                        "finding_id": e["finding_id"],
                        "kind": e["kind"],
                        "note": e.get("note", ""),
                    }
                    for e in state["evidence"]
                ],
                w="local",
            ).consume()
            tx.run(
                """UNWIND $rows AS r MATCH (s:Service:DLRecord {workspace:$w,kind:'Service',key:r.id})
            MERGE (c:DLRecord:CancellationCase {workspace:$w,kind:'CancellationCase',key:r.id})
            SET c.service_status=r.service_status,c.mandate_status=r.mandate_status,c.effective_date=r.effective_date
            MERGE (s)-[:HAS_CASE]->(c)""",
                rows=[{"id": fid, **c} for fid, c in state["cases"].items()],
                w="local",
            ).consume()
            tx.run(
                """UNWIND $rows AS r MATCH (t:Transaction:DLRecord {workspace:$w,kind:'Transaction',key:r.tid}), (c:CancellationCase:DLRecord {workspace:$w,kind:'CancellationCase',key:r.fid}) MERGE (t)-[:REQUIRES_REVIEW]->(c)""",
                rows=[
                    {"tid": a["transaction"]["id"], "fid": a["finding_id"]}
                    for a in result["alerts"]
                ],
                w="local",
            ).consume()

        with self.driver.session() as session:
            session.execute_write(write)

    def graph(self, fid=None):
        if not self.driver:
            return {
                "mode": "sqlite",
                "nodes": [],
                "edges": [],
                "message": "Graph queries require Neo4j mode. This preview does not simulate a Neo4j connection.",
            }
        query = """MATCH (a:DLRecord {workspace:$w})-[r]->(b:DLRecord {workspace:$w})
        WHERE $fid IS NULL OR a.key=$fid OR b.key=$fid OR
        EXISTS { MATCH (a)-[:ATTRIBUTED_TO]->(:Service {workspace:$w,kind:'Service',key:$fid}) } OR
        EXISTS { MATCH (b)-[:ATTRIBUTED_TO]->(:Service {workspace:$w,kind:'Service',key:$fid}) }
        RETURN elementId(a) AS ai, labels(a) AS al, properties(a) AS ap,
        elementId(b) AS bi, labels(b) AS bl, properties(b) AS bp,type(r) AS rel LIMIT 500"""
        records, _, _ = self.driver.execute_query(query, w="local", fid=fid)
        nodes = {}
        edges = []
        for r in records:
            for side in ("a", "b"):
                p = r[side + "p"]
                labels = [l for l in r[side + "l"] if l != "DLRecord"]
                nodes[r[side + "i"]] = {
                    "id": r[side + "i"],
                    "type": labels[0],
                    "label": p.get("name", p.get("key", "")),
                    "properties": p,
                }
            edges.append({"source": r["ai"], "target": r["bi"], "label": r["rel"]})
        return {
            "mode": "neo4j",
            "nodes": list(nodes.values()),
            "edges": edges,
            "limit": 500,
        }

    def delete(self):
        if self.driver:

            def remove(tx):
                tx.run(
                    "MATCH (n:DLRecord {workspace:$w}) DETACH DELETE n", w="local"
                ).consume()
                tx.run(
                    "MATCH (w:Workspace {id:$w}) DETACH DELETE w", w="local"
                ).consume()

            with self.driver.session() as s:
                s.execute_write(remove)
        else:
            self.db.execute("DELETE FROM workspace WHERE id=?", ("local",))
            self.db.commit()

    def close(self):
        if self.driver:
            self.driver.close()
        else:
            self.db.close()
