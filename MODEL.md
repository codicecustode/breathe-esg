# Data Model

## Design goals

The model has to do four things simultaneously: support multiple clients (tenants) on one deployment, preserve the original source data without mutation, produce a clean normalized record that analysts can review, and create an immutable audit trail so nothing can quietly change after sign-off.

---

## Core tables

### Tenant

Single table, UUID primary key. Every other table that contains client data carries a `tenant` foreign key. Queries that cross tenant boundaries are blocked at the application layer — the ViewSets filter by tenant, and eventually this becomes a row-level security policy in Postgres.

UUID PK is deliberate: tenant IDs end up in URLs and API responses. An auto-incrementing integer leaks the total count of clients and makes enumeration trivial.

### DataSource

Links a tenant to a named data source with a type (`SAP`, `UTILITY`, `TRAVEL`). One tenant can have multiple SAP plants as separate DataSource rows. The type drives which parser runs.

### ImportJob

Each file upload creates one ImportJob. Fields:
- `uploaded_file` — stored in `media/imports/`, never deleted (audit requirement)
- `status` — PENDING → PROCESSING → COMPLETED/FAILED
- `row_count` — how many emission records were successfully parsed
- `error_log` — per-row parse errors, newline-separated
- `created_at` — timestamp of the upload

ImportJob is the boundary between "raw file" and "structured data." Nothing in NormalizedEmissionRecord is ever mutated to fix a parser bug — instead, you re-upload and re-process, creating a new ImportJob and new records.

### RawRecord

One row per source row (or JSON entry), storing the original data as-is in a JSONField. Purpose: if an analyst or auditor ever questions a normalized value, we can show them exactly what came in off the wire or out of the file. `is_processed` flags whether a NormalizedEmissionRecord was successfully derived.

This table is append-only in practice. We never update RawRecord rows.

### NormalizedEmissionRecord

The central fact table. Every row represents one measured emission event after normalization:

| Field | Purpose |
|---|---|
| `tenant` | Row-level tenant isolation |
| `raw_record` | Traceability back to the original source row |
| `source_type` | SAP / UTILITY / TRAVEL |
| `activity_type` | Human-readable label (e.g. "Diesel HSD (Plant 1000)", "Air travel DEL→BOM") |
| `quantity` + `normalized_unit` | Always in a standard unit: L, kg, m3, kWh, km, room-nights |
| `scope` | Scope 1 / Scope 2 / Scope 3 (GHG Protocol) |
| `emission_factor` | The factor used at ingestion time (kg CO2e per unit) |
| `calculated_emissions` | `quantity × emission_factor` in kg CO2e |
| `date` | Activity date (doc date for SAP, departure date for travel) |
| `period_start` / `period_end` | Billing period (utility only — bills don't align to calendar months) |
| `suspicious` + `suspicious_reason` | Parser-flagged anomaly |
| `review_status` | PENDING → APPROVED / REJECTED |
| `approved_by` | FK to User who approved |
| `is_edited` + `edit_reason` | Analyst edit tracking |
| `source_metadata` | JSON blob of raw source fields preserved for traceability |
| `created_at` / `updated_at` | Immutable created timestamp; updated_at tracks edits |

**Why store `emission_factor` on each row?** Factors change over time (DEFRA updates annually, India's grid intensity changes each CEA report). If we looked up the factor at query time, historical calculations would drift. Storing the factor at ingestion time means a row's `calculated_emissions` is stable and auditable.

### AuditEvent

Every material change to a NormalizedEmissionRecord creates an AuditEvent:

| Field | Purpose |
|---|---|
| `record` | FK to NormalizedEmissionRecord |
| `action` | CREATED / EDITED / APPROVED / REJECTED / FLAGGED |
| `actor` | FK to User (nullable — some events are system-generated) |
| `timestamp` | Immutable, auto_now_add |
| `note` | Free-text from the actor |
| `snapshot` | JSON copy of the record's key fields at the moment of the event |

The snapshot is critical: if a record is later edited, you can reconstruct what an auditor approved. The AuditEvent table is never modified or deleted.

---

## Multi-tenancy

Row-level isolation via `tenant` FK on every data table. The Django ORM layer filters every queryset by tenant. The application currently uses session auth; in production this would be JWT with the tenant claim in the token.

We deliberately avoided schema-per-tenant (separate Postgres schema per client) for a prototype — it complicates migrations and connection pooling. The row-level approach is correct for this scale.

---

## Scope 1 / 2 / 3 mapping

| Source | Scope | Rationale |
|---|---|---|
| SAP fuel (diesel, gas, LPG) | Scope 1 | Direct combustion of fuels owned/controlled by the company |
| Utility electricity | Scope 2 | Purchased electricity from grid (market-based or location-based) |
| Corporate travel (air, hotel, car rental) | Scope 3 | Category 6 (business travel) under GHG Protocol |

The scope is set at parse time using the emission factor lookup and is stored on NormalizedEmissionRecord. An analyst can override it if the business rules differ (e.g., a leased vehicle might be Scope 1 instead of Scope 3).

---

## Unit normalization

SAP exports quantities in native SAP units (L, KG, M3, TON, ST). We normalize at parse time:

| SAP unit | Standard unit | Notes |
|---|---|---|
| L, LT | L | Liters |
| KG | kg | Kilograms |
| M3, M³ | m3 | Cubic meters (gas) |
| TON, TO | t | Metric tons |
| ST | unit | Pieces — not an emission material |

Utility data is always stored in kWh (computed from opening/closing readings if total_units is absent).

Travel distances are always stored in km (miles converted at ingestion using 1 mi = 1.60934 km).

---

## Source-of-truth tracking

Each NormalizedEmissionRecord carries:
1. `raw_record` FK → the exact source row that produced it
2. `source_metadata` JSON → key source fields (doc number, meter ID, flight number, etc.) preserved verbatim
3. `import_job` (via raw_record) → which file upload, at what time, by which user
4. `created_at` → when the record was created
5. The AuditEvent chain → every subsequent change

This gives a complete chain: auditor asks "where did row 4821 come from?" → source_metadata + raw_record → ImportJob → uploaded_file still on disk.
