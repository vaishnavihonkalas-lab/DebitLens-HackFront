# Three-minute demo

Use only fictional data and a clean workspace. Run the full Neo4j setup and confirm the connected indicator. Before recording, rehearse once, then delete the workspace and reload the initial demo. Do not show credentials or terminal environment variables.

## 0:00–0:25 Problem and discovery

Say: “A charge can be easy to authorise and hard to understand later. DebitLens helps trace recurring payments from the records a user supplies.”

Click Load fictional demo. Mention that six months of fictional records are loaded, with no bank connection. Show the coverage dates and accounts.

## 0:25–1:00 Evidence and price change

Inspect StreamBee. Explain that STREAMBEE and SBEE MEDIA are fictional aliases connected to the same demo service. Show source transactions and the +₹100, +33.4% possible increase. Explain that a different plan, tax or billing period might account for it. No notice in supplied records does not mean the merchant never sent one.

Briefly show that LOCAL GROCER is only a possible pattern and is not included in projected spending. Processor descriptions remain ambiguous.

## 1:00–1:25 Neo4j

Open the selected finding in Evidence Graph. Click a transaction and inspect date/amount properties, then the service and mandate connection. Say: “These connections come from actual Neo4j queries. A supplied mandate reference is evidence, not proof of an active bank mandate.”

## 1:25–2:10 Cancellation evidence

Open Imports. Select StreamBee, load the fictional message, parse, review fields and save. Go to Cancellation Centre. Set service status Supported by supplied confirmation; mandate status Unknown. Request date 2026-09-25, effective date 2026-09-30. Save.

Say: “Service cancellation and mandate revocation are separate. This records user-supplied confirmation. Any actual cancellation happens through the authorised billing provider.” Show the official guide reference.

## 2:10–2:40 Later debit

In Imports choose Use later statement. Preview, then import valid rows. Return to Cancellation Centre. Show the October 5 debit and effective cancellation date. Explain that it requires review; the tool makes no fraud or refund decision.

## 2:40–3:00 Evidence and limits

Export evidence JSON. Say: “The prototype includes data deletion, tested import logic, a working API and a real graph database. Next are authenticated deployment and broader provider integrations. Current findings depend on uploaded coverage.”

Record the browser, not only these talking points. Keep the MP4 under 25 MB. A 3-minute 720p video around 800 kbps video plus 64 kbps audio is usually below the limit; check actual size. No video file is included in the code ZIP.
