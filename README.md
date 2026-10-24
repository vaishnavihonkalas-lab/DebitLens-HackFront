# DebitLens

**Find the charge. Trace the commitment. Verify the cancellation.**

A local, runnable hackFront India Fintech prototype for **The Auto Debits Nobody Can Find**. It discovers payment patterns from uploaded CSVs, explains source evidence, flags possible amount increases, provides billing-channel cancellation guidance, records service and mandate statuses separately, and checks later records for debits requiring review.

## What is included

- React/TypeScript responsive UI with six working screens.
- FastAPI backend, integer-paise analysis engine and validated CSV import.
- **Real Neo4j storage and graph queries**, including evidence and cancellation-review relationships.
- Explicit **SQLite preview** for trying the workflow without Neo4j. This mode does not provide graph queries or qualify by itself as Neo4j use.
- CSV field mapping, structured-message preview, user corrections/splits, evidence JSON and safe CSV exports, persistent records and workspace deletion.
- Unit/API tests, real Neo4j integration test and Playwright browser tests.
- Synthetic examples, Docker configuration and submission documentation.

**This rebuild is based on the pasted requirements and Claude's summary. Claude's source ZIP was not available. Its claimed 23 tests are not inherited or claimed here.**

## Fastest complete setup: Docker Desktop

Prerequisites: Docker Desktop with Compose enabled, approximately 4 GB available memory, and internet for first-time image/package downloads. Open a terminal in the extracted `DebitLens` folder.

1. Copy `.env.example` to `.env` and change `NEO4J_PASSWORD` to a new local password of at least 8 characters. Do not commit `.env`.

   Windows PowerShell:
   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```
   macOS/Linux:
   ```bash
   cp .env.example .env
   ```

2. Start the application:
   ```bash
   docker compose up --build
   ```
3. Wait for Neo4j to become healthy and the backend to start. Open **http://localhost:8080**.
4. The header should say **Neo4j connected**. The backend health endpoint is **http://localhost:8000/api/health** and API documentation is **http://localhost:8000/docs**.
5. Click **Load fictional demo**. No bank account is connected.

To stop: `docker compose down`. To also remove the local database volume: `docker compose down -v` (permanently deletes that database).

**Validation limit:** Docker Compose and image builds were supplied but not executed in the build environment because Docker is unavailable. The app was run and tested directly with an actual Neo4j 5.26 database, FastAPI, Vite and Chromium instead. See `docs/EVALUATION.md`.

## Easy preview without Docker or Neo4j

Prerequisites: Python 3.11+ and Node.js 20.19+ or 22+, npm. Commands run from the project root unless shown otherwise. Initial package installation needs internet.

Terminal 1:
```bash
python -m venv .venv
```
Activate on Windows PowerShell:
```powershell
.venv\Scripts\Activate.ps1
```
Or macOS/Linux:
```bash
source .venv/bin/activate
```
Then:
```bash
python -m pip install -r backend/requirements.txt
python scripts/preview.py
```

Terminal 2:
```bash
cd frontend
npm ci
npm run dev
```
Open **http://localhost:5173**. The header correctly says **SQLite preview · no Neo4j**. Graph view explains that Neo4j is required. Other workflows and exports work. Data persists in `local-data/debitlens.db`.

## Full local setup without Compose

1. Install Neo4j Community 5.26 through Neo4j Desktop or another supported local installation. Use a dedicated database instance for this project and set its password. The application manages one `local` workspace.
2. Install backend/frontend dependencies as above.
3. Set environment variables before starting the backend. Merely creating `.env` does not load it for direct Python startup; Compose loads it automatically.

Windows PowerShell, from `DebitLens`:
```powershell
$env:STORAGE_MODE="neo4j"
$env:NEO4J_URI="bolt://localhost:7687"
$env:NEO4J_USER="neo4j"
$env:NEO4J_PASSWORD="your-local-password"
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
macOS/Linux:
```bash
cd backend
STORAGE_MODE=neo4j NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD='your-local-password' python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
4. In another terminal run `cd frontend`, `npm ci`, `npm run dev` from the root. Open http://localhost:5173.
5. Connectivity requires access to Bolt port 7687. The application creates constraints, so its Neo4j account must have appropriate schema permissions.

## Three-minute judge walkthrough

1. On a clean workspace, load fictional demo records. Inspect StreamBee in the findings table.
2. Show its six monthly transactions, the fictional alias match, and ₹299 to ₹399 (+33.4%) change. This is a possible price increase, not proof of missing notice or wrongdoing.
3. Open **Evidence Graph** for that finding. Click a node to inspect its actual persisted properties. SQLite preview has no live graph.
4. In **Imports**, select StreamBee, load the fictional message, parse it, review its fields, and save it as cancellation evidence.
5. In **Cancellation Centre**, select StreamBee. Set service status to **Supported by supplied confirmation**, mandate status **Unknown**, request date **2026-09-25**, effective date **2026-09-30**, and save. This records user-supplied evidence; it does not cancel externally or verify issuer authenticity.
6. In **Imports**, choose **Use later statement**, preview, and import valid rows. Return to Cancellation Centre to see the October 5 debit requiring review.
7. Export evidence. In Settings you can delete the workspace and start again.

Full script: `docs/DEMO_SCRIPT.md`.

## Supported inputs

CSV required columns: `date,description,amount,direction,account_label,currency`. Dates are `YYYY-MM-DD` or `DD/MM/YYYY`; direction is `debit`/`credit`; amount is positive INR with at most two decimal places (up to ₹100,000,000). Store amounts as integer paise.

Optional: `transaction_id,payment_rail,merchant_reference,mandate_reference,billing_channel,subscription_reference`. Use subscription or mandate references to separate different plans at one merchant. Supported payment rails: `UPI,CARD,NACH,OTHER,UNKNOWN`. Supported guide channels include `UPI,GOOGLE_PLAY,APPLE,DIRECT,CARD,NETFLIX_DIRECT,UNKNOWN`. Map alternative header names before previewing. Field names and channel identifiers are case-sensitive.

Maximum 2 MB CSV, 10,000 rows, and 3 MB API request. Invalid rows are reported and skipped on valid-row import. Structural/size errors reject the import. A preview is required in the UI before committing.

`transaction_id` plus account label is preferred for duplicate matching. Without IDs the fallback is normalized content plus occurrence count. This preserves identical purchases inside a file but cannot distinguish all identical purchases in different overlapping exports. Stable IDs that conflict with previously imported data produce row errors.

Message parsing supports **labelled fields**, not general natural-language extraction. See `samples/message.txt`. Preview and edit fields before saving. Evidence is linked to the user-selected finding; entered metadata does not automatically rewrite transactions or cancellation dates.

## Tests

From `backend` with Python dependencies installed:
```bash
python -m pytest -q
```
This runs 30 tests and skips the live database test unless configured.

For the real Neo4j integration test, point `NEO4J_TEST_URI` at a **dedicated disposable instance** and set `NEO4J_PASSWORD`. The test deletes the `local` workspace before and after its run. Never target a database with valuable DebitLens data.

PowerShell:
```powershell
$env:NEO4J_TEST_URI="bolt://localhost:7687"
$env:NEO4J_PASSWORD="your-local-password"
python -m pytest -q
```
macOS/Linux:
```bash
NEO4J_TEST_URI=bolt://localhost:7687 NEO4J_PASSWORD='your-local-password' python -m pytest -q
```

With backend and Vite running on 8000/5173, from `frontend`:
```bash
npx playwright install chromium
npx playwright test
npm run build
```
Browser workflow tests delete the workspace at the start. Use fictional disposable data only. For the Compose frontend set `E2E_URL=http://localhost:8080`.

From the root:
```bash
python scripts/evaluate.py
python scripts/package.py
```
The secondary evaluation is only two synthetic service groups. It is not a real-world accuracy benchmark or an independently held-out dataset.

## Troubleshooting

- **Backend unavailable:** keep both local terminals open, check `http://localhost:8000/api/health`, and verify port 8000 is free.
- **PowerShell activation blocked:** use `.venv\Scripts\python.exe` directly instead of changing machine-wide execution policy.
- **Python command missing:** use `py -3.11` on Windows or `python3` on macOS/Linux.
- **Neo4j startup error:** check credentials, Bolt connectivity, environment variables, database readiness and schema privileges. Default mode is Neo4j, so preview must be explicitly selected.
- **Compose services fail:** run `docker compose logs neo4j backend frontend`. Initial images and builds need internet. If you changed the password after creating the volume, use the password already stored in that database or reset your disposable volume.
- **UI opens but no data:** load sample records or import supported CSV. A successful UI connection does not by itself prove Neo4j is active; check the header and health endpoint.
- **CSV errors:** use decimal numbers without currency symbols or thousands separators. Correct direction and date formats. Look at row errors after preview.
- **Guide does not match your account:** confirm the billing channel from the receipt. App menus and provider terms change.
- **Tests cannot find a browser:** run `npx playwright install chromium` from `frontend`.

## Important limits

Local single-user application, no login or multi-tenant service. Bound to loopback in documented setups. Do not publish it with real financial data. CORS is not authentication. The public GitHub repository should contain source and synthetic examples only.

No live banking, AA, UPI cancellation, issuer validation, email/SMS sync, PDF/OCR import, production security audit or real customer pilot. No PINs, OTPs or banking secrets requested. Guide links are official reference links; some routes remain generic. All named demo services/aliases are fictional.

Recurring detection is a heuristic. Missing records, variable billing, taxes, discounts, annual renewals and ambiguous processors limit its conclusions. Credits are matched heuristically to earlier equal debits within 45 days. Unknown repeated merchants are not included in projections unless supported by mandate data or user confirmation. Service/mandate evidence is user-supplied, not cryptographically verified.

Corrections can change a finding's grouping ID. Existing evidence and cancellation cases stay linked to the previous ID rather than silently transferring to a different service. Review and re-enter relevant evidence for regrouped findings.

The database stores a workspace snapshot and rebuilds its graph projection per mutation. It is suitable for a small bounded demonstration, not large-scale production. Graph queries return at most 500 relationships. Local history and evidence are editable by database administrators.

The UI shows estimated next dates, not guaranteed future debit schedules. Monthly equivalents use the latest observed amount and inferred cadence, not realised savings or a guarantee that a recorded cancellation failed. Review cancellation status when interpreting projections.

## Project layout

```text
backend/app/          Engine, FastAPI routes, Neo4j/SQLite storage, guide registry
backend/tests/        Engine, API and actual Neo4j integration tests
backend/samples/      Bundled synthetic API examples (mirrors root samples)
frontend/src/         React UI and styles
frontend/e2e/         Playwright workflow and mobile tests
samples/              User-facing synthetic CSVs and message example
docs/                 Architecture, evaluation, idea, demo, sources, disclosure
scripts/              Preview launcher, synthetic evaluation and ZIP packaging
compose.yaml          Full Neo4j/backend/frontend local setup
```

MIT licence applies to original project code. Dependencies keep their own licences. See `LICENSE` and `docs/AI_AND_OPEN_SOURCE_DISCLOSURE.md`.
