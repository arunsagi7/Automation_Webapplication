# 01 — Project Overview

## What this system is

**Creative Scanner Pro** (internal FastAPI app title: `"Creative Scanner Pro"`,
version `2.0.0`) is a multi-tool internal platform for a digital advertising /
media agency. It automates the production of advertising **reports** and
**screenshots** for multicultural ad campaigns (the campaign data is full of
audiences like Vietnamese, Punjabi, Arabic, Mandarin, Hindi, etc.).

Despite the single app name, the codebase is really **five loosely-coupled tools**
served from one FastAPI backend and one static multi-page frontend:

| # | Tool (module) | What it produces | Primary frontend page |
|---|---------------|------------------|-----------------------|
| 1 | **CRM Excel Generator** | A processed `.xlsx`/`.csv` with realistic, de-duplicated Clicks / CTR / VCR / Viewability numbers generated to fit configured ranges | `crm-excel.html` |
| 2 | **Reach Report Generator** | A single consolidated "MPN & CPN Breakdown" Excel workbook merging several per-audience "burst" campaign files | `reach-report.html` |
| 3 | **Final Report Generator** | A 10-sheet campaign report Excel (REACH / DATE / APP URL / TIME OF DAY / EXCHANGE / DEVICE / CREATIVE / CITY / AGE / GENDER), with automated QC | `final-report.html` + `qc-checker.html` |
| 4 | **Creative Scanner** | Live browser screenshots of real websites with the client's ad creative injected into detected ad slots; optional PPTX export | `index.html` |
| 5 | **PPT Store / Reports** | PowerPoint deck of scanned screenshots, plus template management | `ppt-store.html` |

Supporting cross-cutting concerns: **authentication & user management** (JWT +
role-based page access) and a set of **utilities** (Excel↔CSV, health checks,
image base64, gradient blending).

> **Important framing for future work:** modules 1–3 are *data-fabrication /
> report-formatting* tools. They take sparse campaign inputs (often just totals)
> and **synthesize plausible, internally-consistent breakdowns** (per-day, per-city,
> per-device, etc.) using weighted random distribution with sum-preservation, then
> format them into client-ready Excel. This is the core "business logic" of the app
> and is where almost all the complexity lives. See `BUSINESS_LOGIC/BUSINESS_RULES.md`.

## Technology stack [CONFIRMED from requirements.txt / package.json]

**Backend** (`Backend_Screenshot/`)
- Python, **FastAPI 0.111** + **Uvicorn** (ASGI server)
- **SQLAlchemy 2.0** ORM + **Alembic** (migrations exist but startup also uses ad-hoc `ALTER TABLE` guards)
- **psycopg2** for PostgreSQL; **SQLite** for local dev
- **openpyxl 3.1** + **pandas 2.2** — all Excel/CSV reading & writing
- **python-pptx 1.0** — PowerPoint generation
- **Playwright 1.58** (+ `playwright-stealth`) — headless browser scanning
- **Pillow** — image processing
- **python-jose** (JWT) + **bcrypt** — auth
- **anthropic** (Claude Vision) — *optional* AI ad-slot detection

**Frontend** (`Frontend_Screenshot/`)
- **Vanilla JS, no bundler.** Multi-page app: each tool is its own `.html` file
  with inline `<script type="module">` blocks. A small ES-module library exists
  under `src/` (EventEmitter, HTTPClient, StateManager, etc.) used mainly by the
  scanner page.
- Deployed as static files (Netlify config present).

**Databases** — there are **two separate databases** [CONFIRMED]:
- `scanner_db` (default `sqlite:///./scanner.db`) — scanner screenshot results only.
- `ctr_db` (default `sqlite:///./ctr_app.db`) — everything else: users, CRM rules/memory,
  processed-file logs, final-report store, reach-report store, and the
  reference tables `app_url_reference` and `city_reference`.

## Deployment targets [CONFIRMED from configs]

- Backend containerized (`Dockerfile`) and configured for **Render** (`render.yaml`)
  and **Railway** (`railway.toml`). Production DB is **PostgreSQL**.
- Frontend on **Netlify** (`netlify.toml`) which proxies `/api/*` to
  `https://creative-scanner-backend-2.onrender.com`.
- Alternative **Hostinger** deploy assets exist under `hostinger_deploy/`.

## Module summary table

| Module | Purpose | Input | Output | Main files |
|--------|---------|-------|--------|-----------|
| CRM Excel Generator | Generate realistic clicks/CTR/VCR/viewability within configured ranges, de-duplicated vs. yesterday | Uploaded `.xlsx`/`.xls`/`.csv` of DV360-style rows + rules + settings | Processed `.csv` (single sheet) or `.zip` of CSVs (multi-sheet) | `routers/crm.py`, `services/crm_processor.py`, `services/crm_excel_writer.py`, `services/crm_memory.py` |
| Reach Report Generator | Consolidate per-audience burst files into one formatted "MPN & CPN Breakdown" workbook | Multiple campaign `.xlsx` files + a `template` file | One `.xlsx` workbook | `routers/reach_report.py`, `services/reach_parser.py`, `services/reach_generator.py` |
| Final Report Generator | Split a multi-block Excel, then synthesize a 10-sheet campaign report and auto-QC it | Uploaded `.xlsx` (multi-block) → split files; then generate | Per-block report `.xlsx` + QC JSON | `routers/final_report.py`, `services/excel_splitter.py`, `services/report_generator.py` |
| Creative Scanner | Screenshot websites with injected ad creatives | List of URLs + device | NDJSON event stream, screenshots on disk + in DB | `routers/scan.py`, `services/browser.py`, `services/ad_detector.py`, `services/vision_detector.py`, `services/smart_placement.py`, `services/image_utils.py` |
| PPT Store | Build/download PPTX decks from screenshots; manage templates | Screenshot record IDs / uploaded templates | `.pptx` | `routers/ppt_store.py`, `routers/results.py`, `services/ppt_exporter.py`, `services/ppt_style_extractor.py` |
| Auth & Users | Login, JWT, role-based page access | username/password | JWT token; user CRUD | `routers/auth.py`, `routers/users.py`, `core/security.py`, `core/deps.py`, `core/auth.py`, `models/user.py` |
| Utilities | Excel→CSV, health, image base64, PPT assets, gradient | various | various | `routers/utilities.py` |

See each `MODULES/*.md` for full detail.
