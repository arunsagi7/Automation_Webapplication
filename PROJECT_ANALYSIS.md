# Creative Scanner Pro — Project Analysis

**Date:** June 23, 2026 (updated)  
**Codebase size:** ~11,000 lines of Python (backend) + ~800 lines of vanilla JS (frontend)

---

## What the project does

**Creative Scanner Pro** (also branded "AdVision AI" in the frontend) is an **ad verification and simulation platform**. Given a list of URLs and your creative image files, it:

1. Launches a headless Chromium browser via Playwright
2. Detects ad slots on each page (DOM selectors → GPT API → Claude Vision AI fallback)
3. Injects your creatives into those slots with pixel-accurate positioning
4. Takes full-page before/after screenshots
5. Exports branded PowerPoint reports for client presentations
6. Supports both desktop (1920×1080) and mobile (390×844 iPhone) viewports

There is also a **CRM Excel Processor** (`/crm`) and a **Final Report** generator (`/final-report`) — separate feature domains that process campaign performance data (impressions, clicks, CTR, viewability) and produce split Excel reports per language/city.

---

## Project Structure

```
$Screenshot/                       ← git root
├── Backend_Screenshot/            ← Python FastAPI backend (main codebase)
│   ├── main.py                    ← app factory, middleware, routers
│   ├── core/                      ← config, auth, logging, paths
│   ├── routers/                   ← one file per feature (scan, crm, auth, users…)
│   ├── services/                  ← all business logic (browser, ad_detector, ppt…)
│   ├── models/                    ← SQLAlchemy ORM models
│   ├── schemas/                   ← Pydantic request/response schemas
│   ├── database/                  ← two DB engines (scanner_db + ctr_db)
│   └── migrations/                ← Alembic schema versions
├── Frontend_Screenshot/           ← Vanilla JS dashboard (no bundler)
│   ├── index.html / style.css     ← main UI
│   ├── src/modules/               ← Application.js, StateManager, ResultsRenderer…
│   └── src/core/                  ← DOM helpers, EventEmitter, HTTPClient, Logger
├── input_images/                  ← desktop/ and mobile/ creative PNGs
└── screenshots/                   ← generated output (gitignored)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI 0.111 + Uvicorn |
| Browser automation | Playwright 1.58 (Chromium, stealth mode) |
| Image processing | Pillow 12 |
| Report generation | python-pptx, openpyxl, pandas |
| AI detection fallback | Anthropic Claude Vision (haiku) |
| Database ORM | SQLAlchemy 2.0 + Alembic |
| Databases | SQLite (dev) / PostgreSQL (prod) |
| Authentication | JWT (python-jose) + X-API-Key |
| Frontend | Vanilla JS ES modules — no React, no bundler |

---

## Feature Inventory

### Core Scanner
- `POST /process` — streams NDJSON progress events while scanning URLs concurrently
- `GET /results` / `DELETE /results/{id}` — result management
- `POST /results/export-ppt` — PowerPoint export
- `POST /upload-creatives` / `GET /creatives` / `DELETE /delete-creative` — creative management

### PPT Store
- Upload/manage PPTX templates
- Generate and save branded reports

### CRM Excel Processor
- Upload `.xlsx`/`.csv` campaign data
- Apply CTR/VCR/Viewability rules (stored in DB)
- Uses "yesterday memory" (DB-persisted) for delta comparisons
- Returns processed `.xlsx`

### Final Report
- Split campaign Excel files by language/city (from reference DBs)
- QC workflow: mark reports as `in_qc`, record verified metrics
- Download individual output files

### Reach Report
- Separate reach data generation and parsing pipeline

### User Management
- `super_admin` and `admin` roles
- Per-user page access control (`allowed_pages` JSON column)
- JWT login/logout flow

---

## How Ad Detection Works (3-Level Pipeline)

```
Level 1 — DOM selectors
  60+ CSS selectors for Google/DFP, AdSense, common ad class/ID patterns,
  news site patterns, and third-party tags.
  Uses MutationObserver to catch dynamically injected slots.

        ↓  (if < N slots found)

Level 2 — Claude Vision AI  (vision_detector.py)
  Sends page screenshot to Claude, asks it to identify all ad regions
  with bounding boxes. Returns slot dicts compatible with the pipeline.
  Only runs when ANTHROPIC_API_KEY is set (~$0.001/call).

        ↓  (if still no slots)

Level 3 — Smart Placement  (smart_placement.py)
  3a. Structural DOM  — finds header bottom / right sidebar gap
  3b. Claude Vision   — AI picks single best position
  3c. Native Article  — inserts "Sponsored" block between paragraphs
```

---

## Authentication Flow

Two parallel auth methods are accepted on every protected endpoint:

1. **Bearer JWT** — issued by `POST /auth/login`, role-aware
2. **X-API-Key header** — legacy/service-to-service key from `.env`
3. **Dev open mode** — if `API_KEY` is blank and `APP_ENV ≠ production`, all requests pass

---

## Issues & Recommendations

### 🔴 Security

**CORS is fully open**
```python
# main.py line 53
allow_origins=["*"],   # Lock this to your domain in production
```
Even the comment warns about this. Before deploying, set `allow_origins` to your actual frontend domain (e.g. `["https://your-app.render.com"]`).

**Dev open mode in production**
If `API_KEY` is accidentally left blank and `APP_ENV` is not explicitly set to `"production"`, all endpoints are unauthenticated. Make `API_KEY` required in production via config validation.

---

### 🟡 Code Quality

**Two migration strategies running in parallel**
`main.py` startup event runs raw `ALTER TABLE` guards *and* Alembic is also configured. The comment says "Replace this with Alembic" but the guard is still active. Pick one — Alembic — and remove the inline SQL guards. This causes confusion about which is the source of truth.

**`browser.py` is 2,406 lines**
The core Playwright orchestrator is too large. It handles navigation, popup dismissal, stealth init, ad injection, screenshot capture, and concurrency management all in one file. Breaking it into `navigation.py`, `injection.py`, and `concurrency.py` would improve readability and testability.

**`report_generator.py` is 1,157 lines**
Similarly large. Could be split by output type (Excel/PPT/reach).

**`datetime.utcnow` is deprecated (Python 3.12+)**
```python
# models/screenshot.py line 17
created_at = Column(DateTime, default=datetime.utcnow)
```
Replace with `datetime.now(timezone.utc)` to avoid deprecation warnings and future breakage.

**Hardcoded `os.path.join(__file__)` in services**
`ppt_exporter.py` and several other service files compute `_BACKEND_ROOT` from `__file__` instead of using the `core/paths.py` single source of truth. The architecture doc says paths should come from `core/paths.py`, but it isn't consistently followed.

**Legacy `src/index.js` still present**
The frontend has two entry points: the old monolithic `src/index.js` and the new modular `src/main.js`. The ARCHITECTURE.md says `index.js` "can be deleted once the module system is verified complete." It should be deleted to avoid confusion.

---

### 🟢 Strengths

- **Clean router/service split** — routers contain no business logic; all logic is in `services/`
- **Pydantic settings** — all config from environment variables, no hardcoded secrets
- **Streaming NDJSON** — the scan endpoint streams progress events, good UX for long-running jobs
- **Graceful fallbacks** — both `playwright_stealth` and `anthropic` are optional imports; the app works without them
- **IAB size scoring** — image matching uses proper aspect ratio + size scoring against standard IAB sizes
- **Two-database design** — scanner results and CRM/user data are cleanly separated

---

## Priority Action Items

| Priority | Issue | File |
|---|---|---|
| 🔴 High | Set `allow_origins` to specific domain before prod deploy | `main.py:53` |
| 🔴 High | Make `API_KEY` required in production config | `core/config.py` |
| 🟡 Medium | Remove inline `ALTER TABLE` guards, use Alembic only | `main.py:108–144` |
| 🟡 Medium | Replace `datetime.utcnow` with timezone-aware version | `models/screenshot.py:17` |
| 🟡 Medium | Route all path resolution through `core/paths.py` | `services/ppt_exporter.py` etc. |
| 🟢 Low | Delete legacy `src/index.js` | `Frontend_Screenshot/src/index.js` |
| 🟢 Low | Split `browser.py` (~2,400 lines) into smaller modules | `services/browser.py` |
| 🟢 Low | Gitignore generated Excel files in `final_report_outputs/` (100+ files committed) | `.gitignore` |
| 🟢 Low | Migrate `@app.on_event("startup")` to lifespan context manager (deprecated in FastAPI) | `main.py` |
| 🟢 Low | Consolidate nested git repos — `Backend_Screenshot/` has its own `.git` separate from the root repo | repo structure |
