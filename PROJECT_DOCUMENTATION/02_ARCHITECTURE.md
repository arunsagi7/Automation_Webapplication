# 02 — Architecture Overview

## High-level component diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│  FRONTEND (Frontend_Screenshot/) — static multi-page vanilla JS        │
│  login.html  index.html  crm-excel.html  reach-report.html            │
│  final-report.html  qc-checker.html  ppt-store.html                   │
│  API base URL resolved by src/config/apiConfig.js                     │
└───────────────┬──────────────────────────────────────────────────────┘
                │  HTTPS (fetch); Netlify proxies /api/* → Render backend
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  BACKEND (Backend_Screenshot/) — FastAPI app (main.py)                 │
│                                                                        │
│   routers/ (HTTP layer, orchestration)                                 │
│     auth  users  scan  results  creatives  ppt_store  utilities        │
│     crm   final_report   reach_report   screenshot_db                  │
│                     │                                                   │
│                     ▼                                                   │
│   services/ (business logic, no HTTP)                                   │
│     crm_processor / crm_excel_writer / crm_memory                      │
│     reach_parser / reach_generator                                     │
│     report_generator / excel_splitter                                  │
│     browser / ad_detector / vision_detector / smart_placement /        │
│       image_utils / screenshot_storage / db_service                    │
│     ppt_exporter / ppt_style_extractor                                 │
│                     │                                                   │
│         ┌───────────┴───────────┐                                      │
│         ▼                       ▼                                      │
│   core/ (config, paths,   database/ (2 engines)                        │
│    auth, deps, security,    db.py  → scanner_db                        │
│    logging)                 crm_db.py → ctr_db                         │
└─────────┬───────────────────────────┬────────────────────────────────┘
          ▼                           ▼
┌──────────────────┐        ┌───────────────────────────────────────────┐
│  scanner_db      │        │  ctr_db                                    │
│  (SQLite/PG)     │        │  (SQLite/PG)                               │
│  screenshot_     │        │  users, campaign_rules, global_settings,   │
│  results         │        │  processed_files, yesterday_memory,        │
│                  │        │  scan_screenshots, final_report_store,     │
│                  │        │  reach_report_store, app_url_reference,    │
│                  │        │  city_reference                            │
└──────────────────┘        └───────────────────────────────────────────┘
          ▲
          │ Playwright headless Chromium → real websites (scanner only)
          ▼
   External: target websites, Anthropic Claude Vision API (optional)
```

## The three architectural layers [CONFIRMED]

The backend enforces a clean separation (documented in `main.py`'s own docstring):

1. **`main.py`** — application factory ONLY. Creates the FastAPI app, adds CORS,
   mounts static dirs, includes routers, and runs the startup DB-migration guard.
   No business logic.

2. **`routers/`** — the HTTP layer. Each router:
   - Owns request parsing, validation, file I/O, DB reads/writes, and response shaping.
   - Calls into `services/` for the actual computation.
   - Example: `routers/crm.py` reads the upload + rules + memory, calls
     `services.crm_processor.process_rows()`, then persists results.

3. **`services/`** — pure business logic, **no HTTP and (mostly) no DB concerns**.
   `crm_processor.py` explicitly documents: *"No HTTP or DB concerns here; all I/O
   is handled by the router."* (Exceptions: `report_generator.py`,
   `screenshot_storage.py`, `db_service.py`, and the scanner services do touch the DB.)

4. **`core/`** — cross-cutting: `config.py` (env settings), `paths.py` (resolved
   filesystem paths), `security.py` (JWT + bcrypt), `deps.py` / `auth.py` (auth guards),
   `logging.py`.

5. **`database/`** — two independent SQLAlchemy engines (see below).

## Dual-database design [CONFIRMED — this is critical]

There are **two completely isolated databases**, each with its own engine, session
factory, and declarative `Base`. They never share a session.

| | `scanner_db` | `ctr_db` |
|---|---|---|
| Config var | `DATABASE_URL` | `CRM_DATABASE_URL` |
| Engine | `database/db.py` → `engine`, `SessionLocal`, `Base` | `database/crm_db.py` → `crm_engine`, `CrmSessionLocal`, `CrmBase` |
| FastAPI dep | `get_db()` | `get_crm_db()` |
| Tables | `screenshot_results` | `users`, `campaign_rules`, `global_settings`, `processed_files`, `yesterday_memory`, `scan_screenshots`, `final_report_store`, `reach_report_store`, `app_url_reference`, `city_reference` |
| Default (dev) | `sqlite:///./scanner.db` | `sqlite:///./ctr_app.db` |
| Prod | PostgreSQL | PostgreSQL |

**Why two DBs [INFERRED]:** the scanner (`screenshot_results`) was the original app;
the CRM/report tooling (`ctr_db`) was layered on later and kept isolated so "migrations,
table creation, and sessions never cross databases" (quote from `crm_db.py`).

**Note on ORM vs raw SQL [CONFIRMED]:**
- `campaign_rules`, `global_settings`, `processed_files`, `yesterday_memory`,
  `users`, `scan_screenshots`, `screenshot_results` are proper SQLAlchemy ORM models.
- `final_report_store`, `reach_report_store`, `app_url_reference`, `city_reference`
  are **NOT ORM models** — they are created and queried with **raw psycopg2 SQL**
  inside routers/services (`routers/final_report.py`, `routers/reach_report.py`,
  `services/report_generator.py`). `final_report_store`/`reach_report_store` are
  auto-created at import time; the two reference tables are populated by standalone
  root-level migration scripts.

## Standard data pipeline (report modules)

All three report generators follow the same conceptual shape:

```
INPUT (Excel/CSV, often just totals or sparse rows)
   ↓  parse / read (pandas or openpyxl)
   ↓  compute base totals (impressions, clicks)
   ↓  SYNTHESIZE breakdowns  ← weighted random + sum-preserving rescale
   ↓  SANITIZE / de-duplicate (avoid identical values, cap CTR)
   ↓  QC / cross-sheet consistency fix
   ↓  WRITE styled Excel (openpyxl) with exact number formats
OUTPUT (.xlsx / .csv), persisted to disk + DB
```

## Static file mounts [CONFIRMED in main.py]

- `/screenshots` → `screenshots/` dir
- `/creatives`   → `input_images/` dir (note: `input_images` lives at repo root, `../input_images` relative to backend)
- `/ppt-reports` → `ppt_reports/` dir
- `/ui`          → `Frontend_Screenshot/` (SPA, mounted LAST so it doesn't shadow API routes)
- `/` redirects to `/ui/` if `index.html` exists.

## Startup sequence [CONFIRMED in main.py `startup_event`]

1. Log env.
2. `Base.metadata.create_all()` on `scanner_db` (creates `screenshot_results`).
3. Import `models.user` + `models.scan_screenshot`, then `CrmBase.metadata.create_all()`
   on `ctr_db` (creates `users` + `scan_screenshots`).
4. **Ad-hoc column migration guard** on `screenshot_results` — `ALTER TABLE ... ADD COLUMN`
   for 5 newer columns (idempotent; SQLite vs PG syntax branch).
5. Column guard on `processed_files` adding `ad_type`.
6. **Auto-create default `super_admin`** (`username=admin`, `password=admin123`) if the
   `users` table is empty. ⚠️ See `KNOWN_ISSUES` — default creds.

> The `migrations/` folder contains Alembic migrations (`0001_initial_schema`,
> `0002_add_yesterday_memory`, `0003_ctrdb_scan_screenshots`), but the running app
> relies primarily on `create_all()` + the ad-hoc `ALTER TABLE` guards above. Alembic
> appears to be partially adopted. [INFERRED]
