# Tradeoffs

Three things I deliberately did not build, and why.

---

## 1. Asynchronous processing (Celery + Redis)

**What it is:** Running the CSV/JSON parsing pipeline in a background worker rather than synchronously inside the HTTP request.

**Why I didn't build it:** For a prototype with sample files of 20–100 rows, synchronous parsing is fine. The request completes in under a second. Adding Celery requires Redis (or RabbitMQ), worker process management, a results backend, and handling partial failures across process boundaries. That's a full infrastructure layer for a problem that doesn't exist at prototype scale.

**What breaks without it:** Uploading a real SAP procurement export with 50,000 rows will time out the HTTP request (typically 30s on Render/Railway). The import job will show PROCESSING forever with no result. This is the first thing to fix before going to production with a real client.

**How I'd add it:** `celery.task` wrapping `_process_import`, a Redis broker, Django's `django-celery-results` for tracking job state, and a polling endpoint on ImportJob status. The data model already supports this — ImportJob has `status` and `error_log` fields designed for async updates.

---

## 2. PDF utility bill parsing (OCR)

**What it is:** Extracting consumption, meter ID, and billing period from PDF electricity bills rather than requiring a CSV export.

**Why I didn't build it:** OCR on utility bills is genuinely hard. Indian utility bill formats vary by utility (MSEDCL's format differs from TPDDL's differs from BESCOM's), by year (utilities redesign their bills), and by whether the bill is a scanned image or a born-digital PDF. A robust solution requires either a template library per utility or an ML-based document parser. Neither is a one-sprint problem.

**What breaks without it:** Clients whose facilities teams only have PDF bills (not portal CSV access) cannot use this ingestion path. This is a significant real-world gap — many smaller meters aren't on the portal; the bill arrives by email or post as a PDF.

**How I'd add it:** Apache Tika or AWS Textract for text extraction, then regex patterns per utility template for the key fields (consumption, period, meter ID). Or a commercial utility data service like Urjanet that handles the parsing.

---

## 3. Emission factor versioning and client-configurable factors

**What it is:** A database-driven emission factor table where factors are versioned by year and source, configurable per client, and updatable without a code deploy.

**Why I didn't build it:** Hardcoded factors are correct for a prototype that runs a single reporting period. The current DEFRA 2023, CEA 2022-23, and IPCC AR5 factors are the right defaults for an Indian enterprise client today. A factor versioning system — with effective dates, source citations, override capability per tenant, and audit trail for factor changes — is substantial scope.

**What breaks without it:** When DEFRA releases the 2024 factors (typically March of each year), updating the code and redeploying will silently change all future calculations but leave historical records using the old factor (which is correct, per our storage decision). However, if a client wants to use a custom factor for a specific activity (say, a supplier-specific grid factor rather than the national average), there's no way to configure that without modifying code.

**How I'd add it:** `EmissionFactor` model with fields: `source_type`, `activity_keyword`, `factor_value`, `unit`, `scope`, `effective_from`, `effective_to`, `source_citation`, `tenant` (nullable — null means system default). Parser looks up the active factor for a given activity and date at ingestion time. Analysts can add overrides per tenant.
