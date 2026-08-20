# Configuration

All configuration is environment-driven via `core/config.py` (`pydantic-settings`),
loaded from `Backend_Screenshot/.env`. **No secret values are shown here.**

## Environment variables (`core/config.py :: Settings`)

| Variable | Default | Required? | Used by |
|----------|---------|-----------|---------|
| `DATABASE_URL` | `sqlite:///./scanner.db` | Prod: yes | `database/db.py` (scanner_db) |
| `CRM_DATABASE_URL` | `sqlite:///./ctr_app.db` | Prod: yes | `database/crm_db.py` (ctr_db) |
| `API_KEY` | `""` (disabled) | Prod: recommended | `core/auth.py :: require_api_key` (scanner/creatives/ppt/utilities) |
| `ANTHROPIC_API_KEY` | `""` | Optional | `vision_detector`, `smart_placement` (Claude Vision) |
| `ENGINE_NAV_TIMEOUT_MS` | `45000` | No | `browser.py` navigation |
| `ENGINE_CONCURRENCY` | `8` (config) / `5` (.env.example) | No | scan parallelism |
| `HEADLESS` | `true` | No | Playwright launch |
| `SCREENSHOTS_DIR` | `screenshots` | No | `core/paths.py` |
| `INPUT_IMAGES_DIR` | `../input_images` | No | creatives mount |
| `PPT_ASSETS_DIR` | `ppt_assets` | No | PPT assets |
| `PROCESSED_OUTPUTS_DIR` | `processed_outputs` | No | CRM processed CSVs |
| `ALLOWED_ORIGINS` | `""` (allow all) | Prod: set it | CORS in `main.py` |
| `APP_ENV` | `development` | No | logging/env guards |
| `LOG_LEVEL` | `INFO` | No | `core/logging.py` |

**Not in the Settings class but read directly via `os.getenv` in `core/security.py`:**

| Variable | Default | Purpose |
|----------|---------|---------|
| `JWT_SECRET` | `"change-me-in-production-supersecret-key"` | JWT signing. ⚠️ Warns (does not fail) if default is used in production. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | Token lifetime (8h). |
| `PORT` | (unset → 8001) | `run.py` bind port (PaaS injects it; host becomes 0.0.0.0). |

## Secrets — document as references only

- `JWT_SECRET → required in production → core/security.py`
- `API_KEY → optional (protects scanner-family endpoints) → core/auth.py`
- `ANTHROPIC_API_KEY → optional (enables AI vision) → vision_detector / smart_placement`
- `DATABASE_URL`, `CRM_DATABASE_URL → required in production → database/*.py`
  (contain DB credentials — never commit).

## Config files

| File | Purpose |
|------|---------|
| `Backend_Screenshot/.env` / `.env.example` | Backend env vars (`.env` is git-ignored) |
| `Backend_Screenshot/render.yaml` | Render deployment |
| `Backend_Screenshot/railway.toml` | Railway deployment |
| `Backend_Screenshot/Dockerfile` | Container build |
| `Backend_Screenshot/alembic.ini` + `migrations/` | Alembic migrations |
| `Backend_Screenshot/.python-version` | Python version pin |
| `Backend_Screenshot/site_creatives.json` | Per-site → creative mapping (scanner) |
| `Frontend_Screenshot/netlify.toml` | Static host; proxies `/api/*` → `https://creative-scanner-backend-2.onrender.com` |
| `Frontend_Screenshot/src/config/apiConfig.js` | Resolves `API_BASE_URL` (window override → same-origin → `http://127.0.0.1:8001`) |
| `railway.toml` (repo root) | Root-level Railway config |
| `hostinger_deploy/` | Alternative Hostinger deploy assets |

## Frontend API base URL resolution [CONFIRMED]

1. `window.API_BASE_URL` if injected (e.g. in `index.html`).
2. Else same-origin (`window.location.origin`) when not `file://`.
3. Else `http://127.0.0.1:8001` (local dev).

Individual pages also fall back to `window._API` and hardcode
`http://127.0.0.1:8001` as the final default in fetch calls.

## Path resolution (`core/paths.py`)

- `BACKEND_ROOT` = `Backend_Screenshot/` absolute.
- `FRONTEND_DIR` = sibling `Frontend_Screenshot/`.
- `get_paths()` returns absolute dirs for `screenshots`, `input_images` (`../input_images`
  → repo root), `ppt_assets`, `ppt_format` (`PPT_Format`), `ppt_reports`.
- For Render persistent disks, override the `*_DIR` env vars with absolute paths.

## Feature flags / conditional behavior

- **AI vision** is enabled only when `ANTHROPIC_API_KEY` is set; otherwise the scanner
  uses DOM detection + smart placement only (graceful fallback).
- **SQLite vs PostgreSQL** branches appear in `main.py` startup guards, `db.py`,
  `crm_db.py`, and the `final_report_store` DDL (IF NOT EXISTS handling differs).
- **Windows proactor event loop** set only on `win32` and Python < 3.14 (Playwright requirement).
