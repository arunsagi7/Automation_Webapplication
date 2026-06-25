# AdVision AI — Full Project Analysis
*Generated: June 25, 2026*

---

## 1. Project Overview

**AdVision AI** (also called "Creative Scanner Pro") is a full-stack ad-tech platform that automates the detection of ad slots on live websites, injects client creative images into those slots, takes screenshots, and generates reports (PPTX). It is deployed as a SaaS with role-based access control.

| Layer | Technology | Hosting |
|---|---|---|
| Backend API | FastAPI 0.111 + Python 3.x | Render (Singapore, Standard plan) |
| Database (scanner) | PostgreSQL `scanner_db` | Railway |
| Database (users/CRM) | PostgreSQL `ctr_db` | Railway |
| Frontend | Vanilla JS ES Modules | Netlify |
| Browser Automation | Playwright 1.58 + Chromium | Runs inside Render |
| AI Vision | Claude Haiku (claude-haiku-4-5-20251001) | Anthropic API |

---

## 2. Repository Structure

```
$Screenshot/
├── Backend_Screenshot/        # FastAPI application
│   ├── main.py                # App factory, middleware, startup
│   ├── render.yaml            # Render deployment config
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile             # Container definition
│   ├── core/
│   │   ├── config.py          # Pydantic Settings (env vars)
│   │   ├── security.py        # bcrypt + JWT helpers
│   │   ├── auth.py            # API key checker
│   │   ├── deps.py            # FastAPI dependency: get_current_user
│   │   └── paths.py           # Centralised filesystem paths
│   ├── database/
│   │   ├── db.py              # scanner_db SQLAlchemy engine + session
│   │   └── crm_db.py          # ctr_db engine + session (users, CRM)
│   ├── models/
│   │   ├── screenshot.py      # ScreenshotResult ORM model
│   │   ├── user.py            # User ORM model (auth)
│   │   ├── crm.py             # ProcessedFile ORM model
│   │   └── scan_screenshot.py # ScanScreenshot ORM model
│   ├── routers/
│   │   ├── auth.py            # /auth/login, /auth/me, /auth/logout
│   │   ├── users.py           # /users/ — super_admin CRUD
│   │   ├── scan.py            # /process — streaming scan endpoint
│   │   ├── results.py         # /results — list/delete/export PPT
│   │   ├── creatives.py       # /upload-creatives, /creatives, /delete-creative
│   │   ├── utilities.py       # /health, /ping, /get-image-base64, /ppt-export-assets, /convert/excel-to-csv
│   │   ├── crm.py             # /crm/ — Excel→DB pipeline
│   │   ├── final_report.py    # /final-report/ — final campaign reports
│   │   ├── ppt_store.py       # /ppt-store/ — PPT file browser
│   │   ├── reach_report.py    # /reach-report/ — reach/impression reports
│   │   └── screenshot_db.py   # /screenshot-db/ — per-scan screenshot storage
│   └── services/
│       ├── browser.py         # 2,400+ lines — Playwright scan engine
│       ├── image_utils.py     # Creative scoring + matching
│       ├── vision_detector.py # Claude Vision ad-slot detection
│       ├── smart_placement.py # 3-strategy fallback placement
│       ├── crm_processor.py   # Excel CRM ingestion
│       ├── report_generator.py# Campaign report builder
│       ├── ppt_exporter.py    # python-pptx slide generator
│       ├── reach_generator.py # Reach/impression aggregation
│       ├── reach_parser.py    # Reach data parser
│       ├── db_service.py      # DB abstraction helpers
│       └── screenshot_storage.py # Screenshot file management
└── Frontend_Screenshot/       # Vanilla JS SPA
    ├── index.html             # Main app shell
    ├── login.html             # Login page
    ├── src/
    │   ├── app.js             # Entry point
    │   ├── constants/
    │   │   ├── config.js      # API_BASE_URL, endpoint constants
    │   │   └── events.js      # APP_EVENTS enum
    │   ├── core/
    │   │   ├── DOM.js         # DOM query helpers
    │   │   ├── EventEmitter.js# Lightweight pub/sub
    │   │   ├── HTTPClient.js  # fetch() wrapper with streaming
    │   │   └── Logger.js      # Console logger with levels
    │   └── modules/
    │       ├── Application.js # Main controller (~600 lines)
    │       ├── StateManager.js# Centralised reactive state
    │       ├── apiServices.js # API service layer (ScanService, ResultsService, etc.)
    │       ├── ResultsRenderer.js # Results table rendering
    │       └── ToastComponent.js  # Toast notification UI
    └── package.json           # No bundler — devDeps: eslint, prettier, serve
```

---

## 3. Backend Architecture

### 3.1 App Startup (`main.py`)

On every startup the app performs five ordered steps:

1. **Configure logging** — structured log level from `LOG_LEVEL` env var
2. **Create tables** — `Base.metadata.create_all()` for both `scanner_db` and `ctr_db`
3. **Column migration guard** — runs `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` for 5 columns (inline Alembic substitute)
4. **CRM column guard** — adds `ad_type` column to `processed_files`
5. **Admin bootstrap** — if user `admin` exists, **resets password to `Admin@123`** every boot (⚠️ security risk — see §7)

CORS is configured from `ALLOWED_ORIGINS` env var; empty = wildcard `*` (dev only).
Static mounts: `/screenshots`, `/creatives`, `/ppt-reports`. Frontend served at `/ui/` if present.

### 3.2 Configuration (`core/config.py`)

All configuration via Pydantic `BaseSettings` (reads `.env` + env vars). Key settings:

| Setting | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./scanner.db` | Override with PostgreSQL in prod |
| `CRM_DATABASE_URL` | `sqlite:///./ctr_app.db` | Separate DB for users/CRM |
| `API_KEY` | `""` (disabled) | Must set in prod |
| `ANTHROPIC_API_KEY` | `""` | Required for Claude Vision |
| `ENGINE_CONCURRENCY` | `30` | Playwright parallel browsers |
| `ENGINE_NAV_TIMEOUT_MS` | `45000` | Per-page navigation timeout |
| `ALLOWED_ORIGINS` | `""` (wildcard) | Set to Netlify URL in prod |
| `APP_ENV` | `"development"` | Must set to `"production"` on Render |
| `BCRYPT_ROUNDS` | `10` | Lowered from 12 for speed |

### 3.3 Security (`core/security.py`)

- **Password hashing**: `bcrypt` direct (no passlib) — avoids version conflict bugs
- **Rounds**: 10 (~100ms) vs default 12 (~400ms) — 4× faster on constrained Render CPU
- **JWT**: `python-jose`, HS256, 8-hour expiry (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Token payload**: `{sub: user_id, username, role, pages, exp}`
- **Production guard**: CRITICAL log if `JWT_SECRET` is the placeholder string in production

### 3.4 Authentication Flow

```
POST /auth/login (form: username + password)
    ↓
Query ctr_db for active User by username
    ↓
asyncio.to_thread(bcrypt.checkpw) ← non-blocking, offloaded to thread pool
    ↓
Create JWT → return {access_token, role, username, allowed_pages}
```

JWT is stateless. `GET /auth/me` validates the Bearer token and returns user info. Logout is client-side only (no token blacklist).

### 3.5 Role-Based Access

Two roles: `super_admin` (all pages) and `admin` (restricted to `allowed_pages` list).

Pages: `scanner`, `crm_excel`, `ppt_store`, `final_report`, `reach_report`.

Super-admin manages users via `/users/` endpoints (create, update, soft-delete `is_active=False`).

---

## 4. Core Scan Engine (`services/browser.py` — 2,400+ lines)

This is the heart of the platform. Key capabilities:

### 4.1 Browser Hardening (Stealth)
- Disables WebDriver flag, randomises User-Agent + viewport
- Injects canvas fingerprint noise, spoofs WebGL renderer
- Mocks `navigator.plugins`, `navigator.languages`
- Blocks known ad-blocking detection scripts

### 4.2 Network Optimisation
- Blocks image/font/media resources during navigation (speed)
- Intercepts known ad CDN domains to detect competitor ads
- Tracks network requests to identify ad placements

### 4.3 Pre-Scan Hygiene
- **GDPR consent popup dismissal**: clicks common accept buttons by text/aria label
- **Security page detection**: bails out on CAPTCHA / Cloudflare challenge pages
- **Popup/cookie banner dismissal**: common modal patterns

### 4.4 Two-Pass Ad Injection Strategy

**Pass 1 — In-Slot Overlay:**
- Detects existing ad containers in the DOM (iframe, `[class*=ad]`, `[id*=ad]`, etc.)
- Matches creative dimensions to slot size using composite scoring
- Injects creative as a CSS overlay on top of existing ads

**Pass 2 — Smart Placement (fallback):**
Falls through three strategies in order:

| Priority | Strategy | Method |
|---|---|---|
| 1 | Structural DOM | JS finds gaps near nav/header/sidebar using computed layout |
| 2 | Claude Vision | Sends screenshot to Claude Haiku, AI identifies placement zones |
| 3 | Native Article | Injects after 3rd paragraph of article body |

### 4.5 Creative Matching (`services/image_utils.py`)

Composite score determines which creative image best fits a detected slot:

| Factor | Weight | Logic |
|---|---|---|
| Aspect ratio | 40% | Ratio similarity between slot and creative |
| Size coverage | 30% | How much of the slot the creative fills |
| Orientation | 20% | Landscape/portrait/square alignment |
| IAB standard bonus | 10% | Bonus for matching common IAB ad sizes |

- **Hard veto**: mismatched orientation → score = 0, skip
- **Threshold**: 0.50 — below this, no creative is injected
- **Resize**: PIL `contain-fit` resizing preserves aspect ratio within slot bounds
- **Site mapping**: `site_creatives.json` can pin specific creatives to specific domains

### 4.6 Claude Vision (`services/vision_detector.py`)

- Model: `claude-haiku-4-5-20251001` (~$0.001/image)
- Sends screenshot as base64 image with structured prompt
- Returns ad slot candidates with bounding box + confidence
- Filters: confidence > 0.75
- Graceful fallback: returns `[]` if no API key configured
- Runs sync Anthropic client inside `asyncio.to_thread` to avoid blocking

---

## 5. Database Design

### 5.1 `scanner_db` — Screenshot Results

**Table: `screenshot_results`**

| Column | Type | Notes |
|---|---|---|
| id | Integer PK | Auto-increment |
| url | String | Scanned URL |
| screenshot_path | String | Path with injected creative |
| original_screenshot_path | String | Path before injection |
| status | String | `success`, `error`, `no_match` |
| ads_found | Integer | Number of ad slots detected |
| matches_found | Integer | Number of successful injections |
| created_at | DateTime | UTC timestamp |
| matched_creative_name | String | Filename of matched creative |
| matched_creative_size | String | e.g., `728x90` |
| injection_type | String | `overlay`, `smart_placement` |
| device | String | `Desktop` (default) or `Mobile` |

### 5.2 `ctr_db` — Users & CRM

**Table: `users`**

| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| username | String (unique) | Login name |
| hashed_password | String | bcrypt hash |
| email | String | Optional |
| role | String | `admin` or `super_admin` |
| is_active | Boolean | Soft delete flag |
| allowed_pages | JSON/Array | Page access list |
| last_login | DateTime | Updated on login |

**Table: `processed_files`** (CRM)

Tracks Excel files uploaded to the CRM processor. Includes `ad_type` column for creative classification.

**Table: `scan_screenshots`**

Per-URL screenshot records tied to a scan session (separate from `screenshot_results`).

### 5.3 Connection Pooling

Both engines share identical pool config:
```
pool_size=5, max_overflow=10, pool_pre_ping=True, pool_recycle=1800
```
`pool_pre_ping` detects dead Railway connections. `pool_recycle=1800` prevents stale connection errors after 30-minute idle.

---

## 6. Frontend Architecture

### 6.1 Technology Choices

Vanilla JS ES Modules — no framework, no bundler. Pros: zero build step, fast iteration. Cons: no tree-shaking, manual DOM management, growing complexity risk.

### 6.2 Module Map

| Module | Role |
|---|---|
| `Application.js` | Main controller — wires all events, owns scan lifecycle |
| `StateManager.js` | Pub/sub reactive state (scan, results, uploads, UI, VPN) |
| `apiServices.js` | Domain-separated API calls (ScanService, ResultsService, PPTService, etc.) |
| `HTTPClient.js` | `fetch()` wrapper with streaming SSE support |
| `ResultsRenderer.js` | Renders results table with search, select, delete |
| `ToastComponent.js` | Notification toasts |
| `EventEmitter.js` | Lightweight `on()`/`emit()` pub/sub |

### 6.3 Key User Flows

**Scan flow:**
1. User enters URLs (or uploads `.txt` file) + uploads creative images
2. `Application._handleStartScan()` validates inputs → calls `ScanService.startScan()`
3. Backend streams SSE events: `site_start`, `progress`, `match_success`, `no_match`, `error`, `finished`
4. Progress modal shows live log; progress bar fills
5. On `finished` → `SCAN_COMPLETED` emitted → results reloaded from API

**Export flow:**
1. User selects rows (or exports all)
2. `_handleGeneratePPT()` POSTs IDs to `/results/export-ppt`
3. Backend generates PPTX → streams blob response
4. Frontend creates `<a download>` link and triggers browser download

**Creative gallery:**
- Loads from `/creatives` on startup (persists across sessions)
- Upload via drag-and-drop or file picker
- Shows real pixel dimensions + file size
- Delete calls `/delete-creative?filename=...`
- Duplicate prevention (by filename)

---

## 7. Issues & Risks

### 7.1 🔴 Critical: Admin Password Reset Every Boot

**Location**: `main.py`, startup event (~line 161)

Every time the backend restarts, it resets the `admin` user's password to `Admin@123`. This means:
- Any password change to admin is wiped on next deploy or crash-restart
- Anyone who knows `Admin@123` can log in to a freshly restarted instance

**Fix:** Remove the `existing_admin.hashed_password = hash_password("Admin@123")` block. Only create the admin on first boot (when no user exists).

```python
# BEFORE (dangerous)
if existing_admin:
    existing_admin.hashed_password = hash_password("Admin@123")
    existing_admin.role = "super_admin"
    db.commit()

# AFTER (safe)
if not existing_admin:
    default_admin = User(...)
    db.add(default_admin)
    db.commit()
    logger.info("Default super_admin created — change password immediately!")
# If admin already exists, do nothing.
```

### 7.2 🔴 Critical: JWT_SECRET Not Set in Production

**Location**: `core/security.py`

Default placeholder `"change-me-in-production-supersecret-key"` is used unless `JWT_SECRET` env var is set on Render. The code now logs a CRITICAL warning, but the app still boots and tokens are signed with the weak secret.

**Fix**: Set `JWT_SECRET` to the generated 64-char hex secret in Render environment variables. Also set `APP_ENV=production`.

### 7.3 🟡 Medium: Deprecated SQLAlchemy Import

**Location**: `models/screenshot.py`

Uses `from sqlalchemy.ext.declarative import declarative_base` — deprecated since SQLAlchemy 1.4, removed in 2.0+.

**Fix**:
```python
# Replace
from sqlalchemy.ext.declarative import declarative_base
# With
from sqlalchemy.orm import declarative_base
```

### 7.4 🟡 Medium: CORS Wildcard in Production

**Location**: `main.py`

If `ALLOWED_ORIGINS` is empty, CORS allows `*`. This means any website can make authenticated requests to the API.

**Fix**: Set `ALLOWED_ORIGINS=https://creative-scanner-frontend.netlify.app` in Render env vars.

### 7.5 🟡 Medium: Cross-Region Database Latency

Render (Singapore) ↔ Railway (US region). Each DB query adds ~150–200ms round-trip latency.

**Fix**: In Railway, move both databases to `ap-southeast-1` (Singapore/Asia Pacific).

### 7.6 🟡 Medium: Concurrency Too High for Render Standard Plan

`ENGINE_CONCURRENCY=30` is configured. Standard plan (2GB RAM) can safely handle ~8 concurrent Playwright browsers. At 30, the process will OOM-crash mid-scan.

**Fix**: Set `ENGINE_CONCURRENCY=8` in Render env vars.

### 7.7 🟠 Low: No Alembic Migrations

The inline `ALTER TABLE ADD COLUMN IF NOT EXISTS` guards in startup work for adding columns, but cannot handle column renames, type changes, or index management safely.

**Fix**: Adopt Alembic fully. The project already has it in `requirements.txt`.

### 7.8 🟠 Low: VPN Feature Is a Stub

The VPN toggle in the frontend shows a "coming soon" toast. The backend `/api/vpn/status` and `/api/vpn/toggle` always return `connected: false` and `success: false`. This is acceptable as a placeholder but should be hidden in the UI or clearly labelled as "Not Available".

### 7.9 🟠 Low: No Token Refresh / Blacklist

JWT tokens have an 8-hour expiry but there's no refresh endpoint and no revocation mechanism. If a user's account is deactivated, their existing token remains valid until expiry.

**Fix**: Add a short-lived refresh token mechanism, or at minimum check `is_active` on every authenticated request (already done via `get_current_user` — verify this in `core/deps.py`).

---

## 8. Performance Analysis

| Concern | Status | Notes |
|---|---|---|
| Login speed | ✅ Fixed | bcrypt in `asyncio.to_thread`, rounds=10 |
| Cold starts | ✅ Fixed | `/ping` endpoint + cron-job.org every 15min |
| DB connections | ✅ Good | pool_pre_ping + pool_recycle configured |
| Cross-region latency | ⚠️ Ongoing | Render SG ↔ Railway US: ~150-200ms/query |
| Playwright concurrency | ⚠️ Risk | 30 browsers configured, ~8 safe for Standard plan |
| Claude Vision cost | ✅ Low | ~$0.001/image, graceful fallback if no key |

---

## 9. API Endpoint Reference

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/login` | None | Login → JWT |
| `GET` | `/auth/me` | JWT | Current user info |
| `POST` | `/auth/logout` | None | Client-side confirmation |
| `GET` | `/users/` | JWT (super_admin) | List all users |
| `POST` | `/users/` | JWT (super_admin) | Create user |
| `PUT` | `/users/{id}` | JWT (super_admin) | Update user |
| `DELETE` | `/users/{id}` | JWT (super_admin) | Soft-delete user |
| `POST` | `/process` | API Key | Start scan (SSE stream) |
| `GET` | `/results` | API Key | List scan results |
| `DELETE` | `/results/{id}` | API Key | Delete result |
| `POST` | `/results/export-ppt` | API Key | Export PPTX |
| `POST` | `/upload-creatives` | API Key | Upload images |
| `GET` | `/creatives` | API Key | List uploaded images |
| `DELETE` | `/delete-creative` | API Key | Delete one image |
| `GET` | `/health` | None | Liveness probe |
| `GET` | `/ping` | None | Keep-alive (cron target) |
| `GET` | `/get-image-base64` | API Key | Image as data-URL |
| `GET` | `/ppt-export-assets` | API Key | PPT theme + images |
| `POST` | `/convert/excel-to-csv` | API Key | Excel → CSV |
| `POST` | `/crm/upload` | API Key | Upload CRM Excel |
| `GET` | `/crm/results` | API Key | CRM processed data |
| `GET` | `/final-report/` | API Key | Final campaign report |
| `GET` | `/ppt-store/` | API Key | PPT file browser |
| `GET` | `/reach-report/` | API Key | Reach/impression data |
| `GET` | `/screenshot-db/` | API Key | Per-scan screenshot records |

---

## 10. Deployment Checklist

### Render (Backend)
- [ ] `JWT_SECRET` — strong random 64-char hex string
- [ ] `APP_ENV=production`
- [ ] `DATABASE_URL` — Railway PostgreSQL `scanner_db`
- [ ] `CRM_DATABASE_URL` — Railway PostgreSQL `ctr_db`
- [ ] `ALLOWED_ORIGINS=https://creative-scanner-frontend.netlify.app`
- [ ] `API_KEY` — shared secret used by frontend
- [ ] `ANTHROPIC_API_KEY` — for Claude Vision (optional)
- [ ] `ENGINE_CONCURRENCY=8` — safe for Standard plan RAM
- [ ] Persistent disk at `/app/data` (5GB, already in render.yaml)
- [ ] cron-job.org pinging `/ping` every 15 minutes

### Railway (Databases)
- [ ] Move both databases to `ap-southeast-1` region to reduce latency

### Netlify (Frontend)
- [ ] `API_BASE_URL` points to live Render URL (in `src/constants/config.js`)
- [ ] HTTPS enforced (default on Netlify)

### Code Fixes (Recommended)
- [ ] Remove admin password reset from startup (§7.1)
- [ ] Fix deprecated `declarative_base` import (§7.3)
- [ ] Set `ENGINE_CONCURRENCY` env var to 8 (§7.6)

---

## 11. Summary

AdVision AI is a well-structured, production-capable ad-tech platform. The scan engine is sophisticated — stealth fingerprinting, two-pass injection, AI-powered slot detection, and composite creative scoring make it genuinely enterprise-grade. The FastAPI architecture is clean with proper separation (routers → services → DB), and the frontend is organised for a no-bundler codebase.

The most urgent issue is the **admin password reset on every boot** (§7.1) — fix this before any real users are onboarded. The **JWT secret** must be set in Render (done in the previous session). Reducing **concurrency to 8** prevents OOM crashes on the Standard plan.

Everything else is polish and optimisation rather than showstoppers.
