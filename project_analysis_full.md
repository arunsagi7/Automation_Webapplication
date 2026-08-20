# Creative Scanner Pro / AdVision AI — Full Project Analysis

**Date:** 2026-08-05  
**Analyst:** Claude (Cowork)

---

## 1. What This Project Is

**Creative Scanner Pro** (branded in the UI as **AdVision AI**) is an ad verification and simulation platform. It lets a user supply a list of website URLs and their own creative (banner) images. The system then:

1. Opens each URL in a headless Chromium browser
2. Detects all ad slots on the page (via DOM, CSS, Google Publisher Tags, and Claude Vision AI as a fallback)
3. Injects the matching creative into each slot with pixel-accurate positioning
4. Captures full-page before/after screenshots
5. Generates PowerPoint or Excel reports for client presentations

Beyond the core scanner, the platform also includes:
- A **CRM Excel Processor** — normalises and enriches campaign data from raw Excel uploads
- A **Final Report generator** — produces multi-sheet Excel campaign reports (Reach, Date, App URL, Time of Day, Exchange, Device, Creative, City, Age, Gender)
- A **QC Checker** — quality control workflow for verifying generated reports
- A **Reach Report** — impression/click/VCR/viewability reach planning tool
- A **PPT Store** — manage PowerPoint templates and saved reports

---

## 2. Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend framework | FastAPI 0.111 (Python 3.11+) |
| Browser automation | Playwright 1.58 + playwright-stealth |
| AI / Vision | Anthropic Claude Vision API (claude-3 model) |
| ORM / DB | SQLAlchemy 2.0 + Alembic migrations |
| Database (dev) | SQLite (dual: `scanner.db` + `ctr_app.db`) |
| Database (prod) | Railway PostgreSQL (dual databases) |
| Auth | JWT (python-jose) + bcrypt + optional X-API-Key |
| Report generation | python-pptx, openpyxl, pandas |
| HTML parsing | BeautifulSoup4 |
| Frontend | Vanilla JS (ES modules, no bundler) |
| Frontend deployment | Netlify |
| Backend deployment | Render.com (Docker, Standard 2 GB plan) |
| Local dev | `run.py` → uvicorn on port 8001 |

---

## 3. Project Structure

```
$Screenshot/                          ← project root
├── Backend_Screenshot/               ← FastAPI backend
│   ├── main.py                       ← app factory (middleware, routers, mounts)
│   ├── run.py                        ← uvicorn launcher
│   ├── render.yaml                   ← Render deployment config (Docker)
│   ├── railway.toml                  ← Railway deployment config
│   ├── Dockerfile                    ← container build
│   ├── requirements.txt              ← Python dependencies (16 packages)
│   ├── alembic.ini                   ← Alembic config
│   ├── core/                         ← cross-cutting infrastructure
│   │   ├── config.py                 ← Pydantic Settings (all env vars)
│   │   ├── auth.py                   ← JWT + API key dual auth dependency
│   │   ├── security.py               ← JWT creation/verification, bcrypt hashing
│   │   ├── deps.py                   ← role guards (require_admin etc.)
│   │   ├── logging.py                ← structured logging setup
│   │   └── paths.py                  ← filesystem path constants
│   ├── routers/                      ← one file per feature domain
│   │   ├── scan.py           (100L)  ← POST /process (streams NDJSON)
│   │   ├── results.py        (52L)   ← GET/DELETE /results
│   │   ├── creatives.py      (126L)  ← creative upload/list/delete
│   │   ├── ppt_store.py      (172L)  ← PPT template + report management
│   │   ├── utilities.py      (186L)  ← /health, /get-image-base64, VPN
│   │   ├── crm.py            (489L)  ← CRM Excel processor
│   │   ├── final_report.py   (2597L) ← Final report generation ⚠️ Very large
│   │   ├── reach_report.py   (275L)  ← Reach report
│   │   ├── screenshot_db.py  (153L)  ← Screenshot DB queries
│   │   ├── auth.py           (115L)  ← /auth/login, /auth/me
│   │   └── users.py          (179L)  ← User CRUD (super_admin only)
│   ├── services/                     ← business logic (no HTTP concerns)
│   │   ├── browser.py        (2406L) ← Playwright orchestrator ⚠️ Very large
│   │   ├── ad_detector.py    (958L)  ← DOM/CSS/GPT ad slot detection
│   │   ├── report_generator.py(2180L)← Multi-sheet Excel report ⚠️ Very large
│   │   ├── vision_detector.py (160L) ← Claude Vision AI fallback
│   │   ├── smart_placement.py (353L) ← 3-level fallback ad placement
│   │   ├── image_utils.py    (481L)  ← Creative matching (IAB size scoring)
│   │   ├── crm_processor.py  (446L)  ← CRM row processing pipeline
│   │   ├── reach_generator.py(333L)  ← Reach stats generation
│   │   ├── reach_parser.py   (448L)  ← Reach data parsing
│   │   ├── ppt_exporter.py   (210L)  ← PPTX report generation
│   │   ├── ppt_style_extractor.py(394L) ← PPTX theme extraction
│   │   ├── excel_splitter.py (349L)  ← Excel file splitting
│   │   ├── crm_excel_writer.py(119L) ← CRM Excel output
│   │   ├── crm_memory.py     (53L)   ← Yesterday/today memory store
│   │   ├── db_service.py     (126L)  ← CRUD helpers (scanner_db)
│   │   └── screenshot_storage.py(226L) ← Screenshot DB save helpers
│   ├── models/                       ← SQLAlchemy ORM models
│   │   ├── user.py                   ← User (roles: admin, super_admin)
│   │   ├── screenshot.py             ← ScreenshotResult
│   │   ├── scan_screenshot.py        ← ScanScreenshot
│   │   └── crm.py                    ← CampaignRule, GlobalSetting, ProcessedFile
│   ├── schemas/                      ← Pydantic request/response models
│   ├── database/
│   │   ├── db.py                     ← scanner_db engine + session
│   │   └── crm_db.py                 ← ctr_db (CRM) engine + session
│   ├── migrations/                   ← Alembic versions
│   └── tests/
│       ├── test_api.py               ← Integration tests (httpx + mocks)
│       └── test_image_utils.py       ← Unit tests
├── Frontend_Screenshot/              ← Vanilla JS SPA
│   ├── index.html                    ← Scanner dashboard
│   ├── crm-excel.html                ← CRM processor
│   ├── final-report.html             ← Final report
│   ├── qc-checker.html               ← QC workflow
│   ├── reach-report.html             ← Reach report
│   ├── ppt-store.html                ← PPT store
│   ├── login.html                    ← Auth page
│   ├── style.css                     ← Global styles
│   └── src/                          ← ES modules
│       ├── main.js                   ← Entry point
│       ├── modules/
│       │   ├── Application.js        ← Top-level orchestrator
│       │   ├── ResultsRenderer.js    ← Scan result cards
│       │   ├── StateManager.js       ← Centralised UI state
│       │   ├── ToastComponent.js     ← Notifications
│       │   └── apiServices.js        ← All fetch() calls
│       └── core/
│           ├── DOM.js, EventEmitter.js, HTTPClient.js, Logger.js
├── input_images/                     ← Creative uploads (desktop/ + mobile/)
├── screenshots/                      ← Runtime screenshot outputs
├── assets/                           ← Static assets
├── .env                              ← ⚠️ Contains real API key (see Security)
├── railway.toml                      ← Root Railway config
├── requirements.txt                  ← Root placeholder (3 lines)
├── ctr_backup.sql                    ← ⚠️ 28 MB DB backup in repo
└── ctr_db_backup.dump                ← ⚠️ 28 MB DB backup in repo
```

---

## 4. Core Workflow — How the Scanner Works

```
Client (Frontend)
   │
   ▼
POST /process { urls: [...], device: "desktop"|"mobile" }
   │
   ▼
scan.py router → open_website() (browser.py)
   │
   ├── Launch Playwright Chromium (stealth mode, fingerprint masking)
   │
   ├── Pass 1 — Ad Detection
   │   ├── Navigate to URL (timeout: 45s, retries: 3)
   │   ├── Scroll page (up to 6 scrolls, lazy-load trigger)
   │   ├── ad_detector.py — DOM scan: 50+ CSS selectors + GPT API + MutationObserver
   │   ├── smart_placement.py — 3-level fallback placement
   │   └── vision_detector.py — Claude Vision AI (if ANTHROPIC_API_KEY set)
   │
   ├── image_utils.py — Match creative to slot by IAB size scoring
   │
   ├── Pass 2 — Injection + Screenshot
   │   ├── Inject creative image into matched slot (JS overlay)
   │   ├── Wait 1500ms (POST_MASK_WAIT_MS) for render
   │   └── Capture full-page screenshot (before + after)
   │
   ├── db_service.py — Save result to scanner_db
   ├── screenshot_storage.py — Save to ctr_db
   │
   └── Emit NDJSON events back to client (progress → result → finished)
```

Events streamed back:
- `started` — scan started
- `site_progress` — per-URL progress
- `match_found` — ad slot matched
- `result` — scan complete for a URL
- `finished` / `error` — done

---

## 5. Authentication & Authorisation

The system uses **dual auth** — either method grants access:

1. **Bearer JWT** (preferred for frontend) — login via `POST /auth/login`, receive a JWT valid for 8 hours
2. **X-API-Key header** (legacy / service-to-service) — set `API_KEY` env var

**Roles:**
- `super_admin` — full access + user management, all pages always accessible
- `admin` — restricted to pages listed in `allowed_pages` JSON column

**Page access control** maps role's `allowed_pages` to frontend HTML pages:
- `"scanner"` → index.html
- `"crm_excel"` → crm-excel.html
- `"ppt_store"` → ppt-store.html
- `"final_report"` → final-report.html

**Dev open mode:** When `API_KEY` is blank and `APP_ENV != "production"`, all endpoints are accessible without credentials. This is intentional for local development.

---

## 6. Dual Database Architecture

The project uses **two separate databases** — a design choice to separate scanner data from CRM/user data:

| DB | Env Var | Dev Default | Tables |
|----|---------|-------------|--------|
| `scanner_db` | `DATABASE_URL` | `sqlite:///./scanner.db` | `screenshot_results` |
| `ctr_db` | `CRM_DATABASE_URL` | `sqlite:///./ctr_app.db` | `users`, `scan_screenshots`, `processed_files`, `campaign_rules`, `global_settings`, `yesterday_memory`, `app_url_reference`, `city_reference`, `final_report_store` |

In production both point to Railway PostgreSQL instances.

**Mixed DB access patterns** exist: some services use SQLAlchemy ORM sessions (`get_crm_db()`), while others (especially `report_generator.py` and `final_report.py`) use raw `crm_engine.raw_connection()` with manual cursor management. This inconsistency adds complexity.

---

## 7. Deployment Architecture

```
Internet
   │
   ├── Netlify (Frontend_Screenshot/)   ← Static SPA
   │   └── Proxy: /api/* → Render backend
   │
   └── Render.com (Docker — Standard 2 GB)
       └── FastAPI app (port 8000)
           ├── Serves /ui/ (Frontend SPA static files)
           ├── Mounts /screenshots, /creatives, /ppt-reports
           └── Persistent disk: /app/data (5 GB)
               ├── screenshots/
               ├── processed_outputs/
               └── final_report_outputs/
                   │
           ┌───────┴───────┐
           ▼               ▼
   Railway PostgreSQL  Railway PostgreSQL
   (scanner_db)        (ctr_db)
```

Local dev: backend serves frontend from `../Frontend_Screenshot/` via `/ui/` static mount.

---

## 8. Issues & Recommendations

### 🔴 Critical (Security)

**8.1 — API key committed to `.env`**  
The file `.env` in the project root contains a live Anthropic API key:
```
ANTHROPIC_API_KEY=sk-ant-api03-QeAVe2...
```
`.env` is listed in `.gitignore`, but if it was ever tracked before the `.gitignore` was updated, this key may be in git history. **Action: Rotate this key immediately at console.anthropic.com, then verify it is not in any git commit with `git log -p | grep sk-ant`.**

**8.2 — Empty API_KEY in dev**  
`API_KEY=` is blank in `.env`, which enables open-mode access to all endpoints. While intentional for dev, it's easy to forget when testing against a staging environment. Consider using a test key even locally.

**8.3 — Default JWT secret**  
`core/security.py` defaults to `"change-me-in-production-supersecret-key"`. The code does log a CRITICAL warning if this is used in production, but it would be better to make startup fail rather than just warn.

**8.4 — Default admin credentials**  
On first startup with no users, the system creates `admin / admin123`. These need to be changed immediately after deployment — there's no enforcement of this.

---

### 🟡 Architecture / Code Quality

**8.5 — Oversized files**  
Several files are too large and should be split:
- `browser.py` — 2406 lines. Could be broken into: `navigation.py`, `injection.py`, `screenshot.py`, `stealth.py`
- `report_generator.py` — 2180 lines. One function per sheet type would make this more maintainable
- `final_report.py` router — 2597 lines. Most logic belongs in a `services/final_report_service.py` file; the router should just handle HTTP concerns

**8.6 — Alembic migrations not used**  
Alembic is installed and configured, but `startup_event()` in `main.py` still runs raw `ALTER TABLE` guards. These should be replaced with Alembic migrations and `alembic upgrade head` should be called at deploy time. The comment in the code acknowledges this ("Replace this with Alembic once you adopt proper migrations").

**8.7 — Mixed DB access patterns**  
`report_generator.py` and `final_report.py` use raw `crm_engine.raw_connection()` with `%s` placeholders, while other modules use SQLAlchemy ORM. This makes the codebase harder to maintain and test. The raw connection approach also risks connection leaks if exceptions occur before `conn.close()`.

**8.8 — ENGINE_CONCURRENCY default mismatch**  
`core/config.py` defaults `engine_concurrency` to `8`, but `browser.py` reads the env var directly: `int(os.getenv("ENGINE_CONCURRENCY", "50"))`. These two defaults are inconsistent. `browser.py` should use `get_settings().engine_concurrency` instead.

**8.9 — `final_report.py` router calls `_ensure_report_store()` on every request**  
The `_ensure_report_store()` function runs `CREATE TABLE IF NOT EXISTS` on every call to create/download a report. This works but is wasteful — it should be called once at startup.

---

### 🟡 Repository Hygiene

**8.10 — 28 MB SQL backup files in repo**  
`ctr_backup.sql` (28 MB) and `ctr_db_backup.dump` (28 MB) are in the project root. The `.gitignore` lists `*.sql` and `*.dump` as ignored, meaning they're either tracked from before or manually added. These inflate the repository and potentially leak production data. They should be removed (`git rm`) and stored outside the repo.

**8.11 — Stale/unused files**
- `requirements.txt` at the root has only 3 lines and is not the real dependency file (that's in `Backend_Screenshot/requirements.txt`). Confusing.
- `src/ad_placer.py` — a standalone file in the root `src/` with unclear purpose — possibly a legacy prototype
- `hostinger_deploy/` directory — deployment artifacts for a platform the project no longer seems to use
- Frontend's legacy `src/index.js` (mentioned in ARCHITECTURE.md as unused — "can be deleted once the module system is verified complete")
- Multiple migration scripts in root: `migrate_app_url_db.py`, `migrate_city_db.py`, `migrate_to_render.py`, etc. — one-off scripts that have likely already been run

**8.12 — Large Excel/database files in root**
- `Fianl Site for automation (1).xlsx` (225 KB × 2 copies) — note: "Fianl" is a typo of "Final"
- `Fianl_Site_for_automation_standardized.xlsx` (292 KB)
- `App_Url_Database.xlsx` (312 KB)
These are tracked by git despite `*.xlsx` being in `.gitignore` — likely added before the rule was in place.

---

### 🟢 What's Done Well

**8.13 — Clean router/service separation**  
Except for `final_report.py`, the codebase does a good job keeping HTTP concerns in routers and business logic in services. `main.py` is clean — it only wires things together.

**8.14 — Pydantic Settings**  
All configuration comes from env vars via `core/config.py`. No hardcoded URLs or credentials in service code. The `@lru_cache` singleton pattern is correctly used.

**8.15 — Structured logging**  
A dedicated `core/logging.py` with consistent `logger = logging.getLogger(__name__)` usage throughout.

**8.16 — Stealth mode for Playwright**  
`browser.py` applies both `playwright-stealth` and a custom `_STEALTH_INIT_SCRIPT` to mask automation signals, improving success rate on sites with bot detection.

**8.17 — Graceful Claude Vision fallback**  
`vision_detector.py` returns `[]` (not an error) if the API key is missing, the package isn't installed, or the API call fails. Claude Vision is a true enhancement, not a hard dependency.

**8.18 — NDJSON streaming for long-running scans**  
The `/process` endpoint streams NDJSON events instead of blocking on a long response. This gives the frontend real-time progress updates during multi-URL scans.

**8.19 — Dual-auth flexibility**  
Supporting both JWT Bearer tokens (for frontend users) and X-API-Key (for service-to-service calls) is well implemented and cleanly falls back to dev open mode.

**8.20 — Docker deployment with Playwright**  
`render.yaml` correctly uses Docker (not the default Python runtime) because Playwright requires Chromium and its system dependencies, which Docker handles cleanly.

---

## 9. Test Coverage

Coverage is minimal:
- `tests/test_api.py` — 4 tests (health, empty process, export-pdf edge cases)
- `tests/test_image_utils.py` — unit tests for image matching

The core scanner logic (`browser.py`, `ad_detector.py`, `report_generator.py`) has no tests. Given the complexity of these files, at minimum the report generator's calculation logic and the ad detector's scoring should have unit tests.

---

## 10. Planned Features (Not Yet Built)

The frontend sidebar shows several "Coming Soon" placeholders:
- URL Manager
- Image Manager
- VPN Manager
- Tasks
- Reports (analytics)
- Activity Logs
- Settings page

These represent planned but unbuilt features. The VPN-related endpoints exist in `routers/utilities.py` (`/api/vpn/*`) so VPN support may be partially implemented server-side.

---

## 11. Quick-Win Action List

| Priority | Action |
|----------|--------|
| 🔴 | **Rotate the Anthropic API key** — it may be in git history |
| 🔴 | **Check git history for secrets**: `git log -p | grep sk-ant` and consider `git filter-branch` or BFG Repo Cleaner |
| 🔴 | **Change default admin password** after any fresh deployment |
| 🔴 | **Set a strong `JWT_SECRET`** in all environment configs |
| 🟡 | Remove `ctr_backup.sql` and `ctr_db_backup.dump` from repo (`git rm`) |
| 🟡 | Fix `ENGINE_CONCURRENCY` — use `get_settings()` in `browser.py` instead of raw `os.getenv()` |
| 🟡 | Extract `final_report.py` router business logic into `services/final_report_service.py` |
| 🟡 | Move startup `ALTER TABLE` guards to Alembic migrations |
| 🟢 | Delete `Frontend_Screenshot/src/index.js` (confirmed legacy/unused) |
| 🟢 | Move one-off migration scripts to an `archive/` folder or delete them |
| 🟢 | Fix typo: "Fianl" → "Final" in Excel filenames |
| 🟢 | Add unit tests for `report_generator.py` calculation logic |
