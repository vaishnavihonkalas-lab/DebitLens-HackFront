# Architecture

## Implemented

React UI communicates with a same-origin `/api` reverse proxy. FastAPI validates requests, loads one local workspace, runs deterministic analysis, and commits changes to Neo4j. Parameterized Cypher statements persist a workspace snapshot and a derived graph atomically in one write transaction. SQLite preview uses parameterized SQL and clearly disables graph queries.

Modules: `core.py` handles parsing, identity and analysis; `main.py` contains API schemas/routes; `storage.py` owns persistence and Cypher; `guides.py` is the curated guide registry. UI types describe API responses. No third-party tracking or external AI services receive records.

## Graph model and queries

Workspace stores the bounded local snapshot. Private DLRecord nodes carry `workspace`, `kind`, and `key`. Account HAS_TRANSACTION Transaction. Transaction DESCRIBED_AS MerchantDescriptor, ATTRIBUTED_TO Service, and optionally REFERENCES Mandate. Service BILLED_THROUGH BillingChannel, SUPPORTED_BY Evidence, and HAS_CASE CancellationCase. Relevant Transaction REQUIRES_REVIEW CancellationCase.

Uniqueness constraints: Workspace.id and composite DLRecord(workspace, kind, key). An index supports workspace matching. There are no cross-user merges; this version deliberately supports only one local user, not multiple authenticated accounts.

Queries in `Store.graph` filter the evidence relationships around a selected finding. The response contains database-derived nodes/edges, node properties and relationship types. `/api/health` verifies actual driver connectivity. SQLite never fakes the graph.

## Why a graph

A finding joins transactions, descriptions, services, billing channels, messages and cancellation events. Traversing those relationships explains how a charge relates to an unresolved cancellation. A relational schema would also work. Neo4j is used to persist and query the relationship evidence, not as proof of identity or cancellation authority.

## Tradeoffs

Rules are inspectable and deterministic, without paid AI calls or a weakly trained classifier. Known aliases are fictional demo entries. Unknown merchants remain reviewable; processor names do not identify services. Snapshot plus graph rebuild keeps a bounded single-user prototype simple and atomic, but rewrites the projection, changes Neo4j element IDs and scales poorly. The Python lock serializes local mutations within one process; do not run multiple backend workers.

Money uses integer paise. Cadence uses calendar-month arithmetic with tolerances. Credits cancel one earlier equal debit within 45 days: this is a disclosed heuristic, not an authenticated refund match. Data history is editable and is not a ledger.

## Future, not implemented

Authenticated workspaces, incremental graph updates, provider-level isolation, encrypted data management, broader statement adapters, PDF/OCR, audited production deployment, account-aggregator partnerships, verified callbacks and official partner cancellation APIs. No live integration is implied by the current local application.
