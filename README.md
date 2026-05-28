# Breathe ESG — Carbon Accounting Platform

**Live Demo:** https://breathe-esg-khaki-ten.vercel.app/
**Backend API:** https://breathe-esg-yug9.onrender.com/api/

A full-stack carbon emissions tracking prototype built for the Breathe ESG tech intern assignment. Ingests data from SAP fuel/procurement exports, utility electricity bills, and Concur travel reports, normalizes them into a unified emissions ledger, and provides an analyst review dashboard with approve/reject workflows and a full audit trail.

---

## Architecture

```
breathe_esg_assignment/
├── backend/          # Django 4.2 + Django REST Framework
│   ├── config/       # Django settings, URLs, WSGI
│   ├── emissions/    # Core app: models, serializers, views, parsers
│   │   └── parsers/  # sap.py, utility.py, travel.py
│   └── requirements.txt
├── frontend/         # React 18 + Vite 5
│   └── src/
│       ├── pages/    # Dashboard, Upload, Review
│       └── api.js    # Axios API client
└── sample_data/      # Test CSV and JSON files
```

---

## Features

- **Multi-source ingestion** — SAP semicolon CSV (German headers), utility electricity CSV (flexible column aliases), Concur travel JSON
- **Emissions calculation** — IPCC AR5 (Scope 1), CEA India 2022-23 (Scope 2), DEFRA 2023 + Cornell HSBI (Scope 3)
- **Haversine fallback** — great-circle flight distance when Concur Distance field is absent
- **Suspicious record flagging** — automatic detection of anomalous quantities (e.g. 52,000 L diesel)
- **Analyst review workflow** — approve/reject with notes, full audit trail per record
- **Multi-tenancy** — all data scoped to a Tenant

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

USE_SQLITE=true python manage.py migrate
USE_SQLITE=true python manage.py createsuperuser
USE_SQLITE=true python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/api/`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`. The Vite dev server proxies `/api` to `http://127.0.0.1:8000`.

---

## Environment Variables

### Backend (Render)

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `true` / `false` (default `false`) |
| `DATABASE_URL` | Full PostgreSQL connection URL from Render |
| `FRONTEND_URL` | Deployed frontend URL (for CORS) |

`USE_SQLITE=true` can be set locally to skip PostgreSQL.

### Frontend (Vercel)

| Variable | Description |
|---|---|
| `VITE_API_URL` | Deployed backend URL, e.g. `https://breathe-esg-yug9.onrender.com` |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET/POST | `/api/tenants/` | List / create tenants |
| GET/POST | `/api/data-sources/` | List / create data sources |
| GET/POST | `/api/emissions/` | List emission records (filterable by scope, status, source) |
| GET | `/api/emissions/summary/` | Aggregated totals by scope, source, status |
| POST | `/api/emissions/{id}/approve/` | Approve a record with optional note |
| POST | `/api/emissions/{id}/reject/` | Reject a record with optional note |
| GET/POST | `/api/import-jobs/` | List / upload import jobs |
| GET | `/api/audit-events/` | Audit trail (filter by `record_id`) |

---

## Sample Data

| File | Source | Rows | Notes |
|---|---|---|---|
| `sample_data/sap_fuel_procurement.csv` | SAP | 20 | Semicolon-delimited, German headers, latin-1 encoding, 1 suspicious row |
| `sample_data/utility_electricity.csv` | Utility | 15 | 3 meters, non-calendar billing periods |
| `sample_data/travel_concur_export.json` | Concur | 4 reports | Missing Distance fields to test haversine fallback |

Upload all three via the **Upload** page to populate the dashboard (49 total records after parsing).

---

## Deployment

- **Backend**: Render Web Service — `build.sh` runs `pip install`, `collectstatic`, `migrate`; start command is `gunicorn config.wsgi`
- **Frontend**: Vercel — set `VITE_API_URL` to the Render service URL, add Render `FRONTEND_URL` to match

---

## Documentation

| File | Contents |
|---|---|
| `MODEL.md` | Data model and schema decisions |
| `DECISIONS.md` | Key architectural and implementation decisions |
| `TRADEOFFS.md` | Trade-offs made during design and development |
| `SOURCES.md` | Emission factor sources and references |
