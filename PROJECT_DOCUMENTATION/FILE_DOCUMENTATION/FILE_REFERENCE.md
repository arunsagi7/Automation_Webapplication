# File Reference

Line counts are approximate (from `wc -l` at documentation time). Paths are relative
to the repository root unless noted. Backend files are under `Backend_Screenshot/`.

## Backend — application core

| File | ~Lines | Purpose | Used by |
|------|-------:|---------|---------|
| `main.py` | 200 | FastAPI app factory: CORS, static mounts, router include, startup DB guard + default super_admin | Uvicorn entrypoint (`main:app`) |
| `run.py` | ~30 | Local/Prod uvicorn launcher (Windows proactor loop, PORT env) | CLI / PaaS |
| `core/config.py` | ~65 | `Settings` (pydantic-settings) — all env vars; `get_settings()` cached | everywhere |
| `core/paths.py` | ~40 | Resolved absolute paths (`get_paths()`), `FRONTEND_DIR`, `BACKEND_ROOT` | main, routers |
| `core/security.py` | ~70 | JWT create/decode, bcrypt hash/verify | auth, deps |
| `core/deps.py` | ~65 | `get_current_user`, `require_admin`, `require_super_admin` | users, auth-gated routes |
| `core/auth.py` | ~30 | `require_api_key` legacy guard | scanner/creatives/ppt/utilities |
| `core/logging.py` | ~30 | `configure_logging()` | main |
| `database/db.py` | ~50 | `scanner_db` engine/session/Base, `get_db()` | scanner services |
| `database/crm_db.py` | ~50 | `ctr_db` engine/session/CrmBase, `get_crm_db()` | crm/reach/final/users |

## Backend — models & schemas

| File | Tables / Schemas | DB |
|------|------------------|-----|
| `models/crm.py` | `CampaignRule`, `GlobalSetting`, `ProcessedFile`, `YesterdayMemory` | ctr_db |
| `models/user.py` | `User` (roles, allowed_pages) | ctr_db |
| `models/scan_screenshot.py` | `ScanScreenshot` (binary screenshots) | ctr_db |
| `models/screenshot.py` | `ScreenshotResult` | scanner_db |
| `schemas/crm.py` | `CampaignRule`, `GlobalSettings` (Pydantic) | — |
| `schemas/creatives.py`, `schemas/results.py`, `schemas/scan.py` | request/response DTOs | — |

## Backend — routers (HTTP layer)

| File | ~Lines | Prefix | Key endpoints |
|------|-------:|--------|---------------|
| `routers/crm.py` | 489 | `/crm` | `/process`, `/rules` CRUD, `/processed-files`, `/download/{f}` |
| `routers/final_report.py` | 2597 | `/final-report` | `/process`, `/generate`, `/languages`, `/cities`, `/reports*`, `/update-app-urls`, QC endpoints |
| `routers/reach_report.py` | 275 | `/reach-report` | `/upload`, `/generate`, `/history*` |
| `routers/scan.py` | 100 | — | `/process` (NDJSON scan) |
| `routers/screenshot_db.py` | 153 | `/db-screenshots` | list/meta/image/original/delete/save |
| `routers/creatives.py` | 126 | — | upload/list/delete creatives |
| `routers/results.py` | 52 | `/results` | list/delete/export-ppt |
| `routers/ppt_store.py` | 172 | `/ppt-store` | templates + export + reports |
| `routers/auth.py` | 115 | `/auth` | login/me/logout |
| `routers/users.py` | 179 | `/users` | user CRUD (super_admin) |
| `routers/utilities.py` | 186 | — | excel→csv, health, image-base64, vpn |

## Backend — services (business logic)

| File | ~Lines | Purpose | Depends on |
|------|-------:|---------|-----------|
| `services/crm_processor.py` | 446 | CRM row generation (`process_rows`, `OUTPUT_COLUMNS`) | stdlib only |
| `services/crm_excel_writer.py` | 119 | `build_excel()` styled xlsx | openpyxl, crm_processor |
| `services/crm_memory.py` | 53 | yesterday_memory load/save | SQLAlchemy, models.crm |
| `services/reach_parser.py` | 448 | Parse burst/template files → dataclasses | openpyxl |
| `services/reach_generator.py` | 333 | Build MPN & CPN Breakdown workbook | openpyxl, reach_parser |
| `services/report_generator.py` | 2180 | Synthesize + write 10-sheet report | pandas, openpyxl, crm_db |
| `services/excel_splitter.py` | 349 | Split multi-block workbook | openpyxl |
| `services/browser.py` | 2406 | Playwright scan orchestration | playwright, ad_detector, image_utils, vision, smart_placement, db_service, screenshot_storage, ppt_style_extractor |
| `services/ad_detector.py` | 958 | DOM ad-slot detection | playwright |
| `services/vision_detector.py` | 160 | Claude Vision detection (optional) | anthropic |
| `services/smart_placement.py` | 353 | Fallback placement strategies | playwright, anthropic |
| `services/image_utils.py` | 481 | Creative selection/resize, site mapping | PIL |
| `services/screenshot_storage.py` | 226 | ctr_db scan_screenshots CRUD | SQLAlchemy |
| `services/db_service.py` | 126 | scanner_db screenshot_results CRUD | SQLAlchemy |
| `services/ppt_exporter.py` | 210 | Build PPTX from screenshots | python-pptx, PIL |
| `services/ppt_style_extractor.py` | 394 | Extract theme/colors/assets from PPTX | python-pptx |

## Backend — migrations, config, data dirs

- `migrations/versions/0001_initial_schema.py`, `0002_add_yesterday_memory.py`,
  `0003_ctrdb_scan_screenshots.py` — Alembic revisions. `alembic.ini`, `migrations/env.py`.
- `requirements.txt`, `Dockerfile`, `render.yaml`, `railway.toml`, `.python-version`,
  `.env` / `.env.example`.
- Data dirs (runtime outputs): `screenshots/`, `processed_outputs/`,
  `final_report_outputs/`, `reach_report_outputs/`, `ppt_reports/`, `ppt_assets/`,
  `extracted_ppt_media/`, `PPT_Format/`, `browser_data*/`.
- `site_creatives.json` — per-site creative mapping. `scanner.db` — local SQLite.

## Frontend (`Frontend_Screenshot/`)

| File | Purpose |
|------|---------|
| `login.html` | Login page → `/auth/login`, stores JWT |
| `index.html` | Scanner UI (also injects `window.API_BASE_URL`) |
| `crm-excel.html` | CRM Excel Generator UI (`/crm/*`) |
| `reach-report.html` | Reach Report UI (`/reach-report/*`) |
| `final-report.html` | Final Report UI (`/final-report/*`) |
| `qc-checker.html` | QC review UI |
| `ppt-store.html` | PPT template/report UI |
| `src/config/apiConfig.js` | Resolve `API_BASE_URL` |
| `src/core/*` | `EventEmitter`, `HTTPClient`, `DOM`, `Logger` |
| `src/modules/*` | `Application`, `StateManager`, `ResultsRenderer`, `ToastComponent`, `apiServices` |
| `src/services/apiService.js`, `src/constants/*`, `src/utils/helpers.js`, `src/lib/utils.js` | supporting JS |
| `style.css`, `src/styles/variables.css` | styling |
| `netlify.toml` | static host + `/api/*` proxy to Render backend |
| `package.json` | dev tooling only (serve/eslint/prettier); no runtime deps |

## Root-level scripts

See `MODULES/OTHER_MODULES.md → Standalone maintenance scripts`. These are manual DB
migration / admin utilities and are **not** imported by the running app.

## Pre-existing docs in repo (superseded by this folder)

`ARCHITECTURE.md`, `README.md`, `DEPLOY.md`, `project_analysis.md`,
`project_analysis_full.md`, `AdVision_AI_Project_Analysis.md`, `scanner_audit_report.md`,
`Backend_Screenshot/CORE_ENGINE.md`, `Backend_Screenshot/README.md`. Treat these as
historical; this `PROJECT_DOCUMENTATION/` folder is the verified reference.
