# DebitLens

## Problem and users

For hackFront India's Fintech problem, The Auto Debits Nobody Can Find, DebitLens helps Indian students and early-career professionals understand recurring debits spread across transaction records and billing channels. Confusing descriptions, unnoticed amount changes and unclear cancellation routes make it difficult to know what remains payable.

## Solution

Users import CSV records and selected labelled billing messages. A deterministic engine identifies payment patterns, provides an evidence assessment and shows exact supporting transactions. It flags possible price increases with amount/date comparisons. Users follow billing-channel guidance, then separately record service cancellation and mandate revocation. Later imports can reveal debits after a recorded effective cancellation date for review.

## Differentiation hypothesis

The product combines evidence tracing, explicit uncertainty, channel-aware cancellation guidance and checks after cancellation. Subscription tracking already exists; this project does not claim a unique invention or proven product-market fit. Its hypothesis is that connecting a suspicious charge to the full cancellation evidence helps users complete a difficult task more reliably than reminders alone.

## Technical implementation

React/TypeScript frontend, Python/FastAPI backend and Neo4j persistence with real relationship queries. Graph paths connect transactions to descriptors, services, billing channels, mandate references and cancellation cases. Workspace snapshot and projection updates are atomic. Integer paise avoids floating-point money calculations. SQLite preview is optional and clearly lacks Neo4j queries.

## Feasibility in India

CSV and selected-message input lets the initial product operate without privileged bank access or a payment partnership. No banking credentials are collected and real cancellation happens at the billing provider. Users retain control over records and can delete their local workspace. Live AA or bank integrations require later partnerships and are not claimed.

## Validation and limits

See EVALUATION.md for actual test results. Test data is synthetic and narrow; no customer savings, market adoption or general detection accuracy is established. The application is local single-user software, with no bank sync, real cancellation execution or production security certification. A user pilot should measure whether people identify charges correctly and successfully follow verified cancellation routes.
