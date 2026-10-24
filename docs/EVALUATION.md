# Evaluation and validation

## Judging criteria

| Criterion | Evidence in this implementation | Boundary |
|---|---|---|
| Problem and track alignment | Finds recurring patterns, compares amounts, routes cancellation, checks later debits; real Neo4j backend | Upload coverage determines visibility; no claim to find every mandate |
| Innovation and effectiveness | Evidence paths, uncertain matching, independent service/mandate statuses, post-cancellation review | Differentiation is a hypothesis; competing trackers exist |
| Technical implementation | React/TypeScript, FastAPI schemas, modular engine/storage/guides, constraints, parameterized Cypher, atomic updates | Local single-user design; whole graph projection rebuilt per mutation |
| Functionality and validation | Runnable sample journey, API tests, real database integration, Playwright workflow and mobile test | Small synthetic fixtures; not a customer or production benchmark |
| Critical thinking and practical implementation | Processor ambiguity, discretionary purchases, refund heuristics, effective dates, billing channels, honest connection indicator | Complex real statements and cancellation contracts need more validation |

## Checks executed on 23 October 2026

- **31 backend tests passed**, including an actual Neo4j Community 5.26.0 integration test.
- **2 Playwright/Chromium tests passed**: full sample workflow and mobile no-page-overflow check.
- TypeScript compilation and Vite production build passed.
- The packaged ZIP was extracted into a fresh directory. `npm ci`, production build, all 31 backend tests against actual Neo4j, and both browser tests passed from that extracted source. ZIP integrity and required-file checks passed.
- Desktop and 390px mobile screenshots inspected. The selected-finding graph view was also inspected.
- Compose YAML parses successfully. **Docker builds and Compose startup not run**, because the build environment has no Docker executable.
- Backend executed on Python 3.12. The source targets Python 3.11+; Python 3.11 itself was not separately exercised.
- Actual graph test used a dedicated local disposable Neo4j process with authentication disabled for the test instance. Graph persistence/Cypher executed, but the password-authentication flow and Docker health check were not verified. The shipped configuration requires authentication and a local password.

Raw backend and browser results are in `backend-test-results.txt` and `browser-test-results.txt`. An unconfigured local pytest run intentionally skips the real database test: this is not equivalent to all layers passing.

## What the tests cover

Invalid amounts, integer paise, dates, month-end and annual cadence, recurring/possible classifications, ₹299/₹399 arithmetic, unknown processors, discretionary purchases, repeated-file deduplication, preserved identical purchases, conflicting stable IDs, unsupported currency, header mapping, refund matching, distinct subscription references, transaction corrections, user rejection, message grammar, CSV-formula protection, missing findings, request size, evidence-required confirmation, valid-row import, later-debit alerts, persistence access, exports, deletion and actual graph relationships.

The database test creates a sample, attaches cancellation evidence and a case, imports a later statement, checks REQUIRES_REVIEW and filtered graph queries, and deletes its test workspace. The browser test performs the workflow through real UI controls against a running backend and database.

## Secondary synthetic evaluation

`samples/heldout.csv` contains two service groups: one known fictional subscription, one repeating café purchase. `scripts/evaluate.py` treats inclusion in the recurring monthly projection as the binary prediction. The result on this tiny file is TP=1, TN=1, FP=0, FN=0, giving precision 1/1 and recall 1/1. **This is a development-time check, not independent held-out validation and not a general 100% accuracy claim.** The filename alone does not establish a proper held-out methodology.

No meaningful general merchant-resolution accuracy or price-alert accuracy is established from this dataset. A useful next study needs independently labelled statements, distinct users/providers, hidden cases and more negative examples. Report denominators and uncertain cases, not only percentages.

## Remaining limitations

- No bank, AA or provider API integration, actual mandate revocation, email/SMS ingestion, PDF/OCR or production authentication.
- Only INR and documented CSV/message formats. No pending/posted distinction in the canonical format; later-debit alerts always require review for timing or final-charge explanations.
- Generic bank/card instructions remain unverified. Other official guides were retrieved for preparation on the recorded date, but were not executed with real provider accounts.
- Safe deduplication without IDs is fundamentally imperfect. Refund matching is heuristic, not based on verified original-transaction links.
- Different subscriptions without distinguishing references can be grouped together. Corrections that change a grouping ID do not migrate old evidence automatically.
- Monthly equivalents reflect last observed price and cadence, not actual future debits or realised savings. They can include a service with a cancellation case pending review.
- Only one workspace and one backend process are supported. Do not make this public with private data. Graph result size is capped, and storage volume backup deletion is outside application deletion.
- No load, penetration, full accessibility, multi-browser or real user testing performed.

The current deliverable is an interactive, tested prototype with real graph integration, not production financial infrastructure.
