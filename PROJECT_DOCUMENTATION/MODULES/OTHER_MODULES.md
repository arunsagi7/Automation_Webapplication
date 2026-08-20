# MODULE — Other Modules (Scanner, PPT, Auth, Utilities)

These modules exist beyond the three report generators named in the request.

---

## 1. Creative Scanner (the original core app)

**Purpose:** launch a headless browser, visit a list of URLs, detect ad slots,
inject the client's creative image into them, and screenshot the result
(before + after). Streams progress back to the browser as NDJSON.

**Files**
| File | Role |
|------|------|
| `routers/scan.py` | `/process` endpoint; NDJSON event streaming |
| `services/browser.py` (2406 lines) | Playwright orchestration: navigation, popup/consent handling, slot detection, creative injection, screenshot, DB save |
| `services/ad_detector.py` (958 lines) | DOM-based ad-slot detection (CSS selectors + mutation observer JS) |
| `services/vision_detector.py` | Optional Claude Vision ad detection (needs `ANTHROPIC_API_KEY`) |
| `services/smart_placement.py` | 3-strategy fallback when no slots found (Structural DOM → Claude Vision → native article insertion) |
| `services/image_utils.py` | Creative selection/matching per site (`site_creatives.json`), resize to slot |
| `services/screenshot_storage.py` | Persist screenshots (binary) to `ctr_db.scan_screenshots` |
| `services/db_service.py` | CRUD for `scanner_db.screenshot_results` |
| `routers/screenshot_db.py` | Serve/list/delete screenshot records + images from `ctr_db` |
| `routers/creatives.py` | Upload/list/delete creative images (`input_images/`) |
| `routers/results.py` | List/delete scan results; export PPT |

**Endpoints**
- `POST /process` — scan URLs (`{urls, device}`); NDJSON stream. `require_api_key`.
- `POST /upload-creatives`, `DELETE /delete-creative`, `GET /creatives`, `GET /creatives/debug`.
- `GET /results`, `DELETE /results/{id}`, `POST /results/export-ppt`.
- `/db-screenshots/` list, `/{id}` meta, `/{id}/image`, `/{id}/original`, `DELETE /{id}`, `POST /save`.

**Detection pipeline (`browser.py`)** — per URL, concurrency-limited by
`ENGINE_CONCURRENCY`:
1. Launch Chromium + stealth; block heavy/ad resources; strip CSP so injection JS runs.
2. Navigate with retry (`_navigate_with_retry`), close popups/consent/overlays,
   detect security-verification pages.
3. Slot detection tiers: `ad_detector.detect_ad_slots` (DOM) → `vision_detector`
   (Claude, optional) → `smart_placement.find_smart_placement` (fallback).
4. Match a creative (`image_utils.find_best_match`, mapping in `site_creatives.json`),
   resize to slot, inject as a `data-injected` overlay via `page.evaluate`.
5. Screenshot (focused on the injected creative); save PNGs to `screenshots/`.
6. Persist: `db_service.save_screenshot_result` (scanner_db) +
   `screenshot_storage.save_screenshot_to_db` (ctr_db binary).

**External services:** target websites (live); Anthropic Claude Vision (optional,
Haiku model, ~\$0.001/call per smart_placement docstring).

**Config knobs:** `HEADLESS`, `ENGINE_CONCURRENCY`, `ENGINE_NAV_TIMEOUT_MS`,
`ANTHROPIC_API_KEY`.

**Data model — `scanner_db.screenshot_results`** (`models/screenshot.py`):
`id, url, screenshot_path, original_screenshot_path, status, ads_found, matches_found,
created_at, matched_creative_name, matched_creative_size, injection_type, device`.

**Data model — `ctr_db.scan_screenshots`** (`models/scan_screenshot.py`): full metadata +
`screenshot_data`/`original_data` (BYTEA binary), `mime_type`, `file_size_kb`, `match_score`, etc.

---

## 2. PPT Store & Report Export

**Purpose:** turn scanned screenshots into a PowerPoint deck matching a client
template, and manage `.pptx` templates.

**Files:** `routers/ppt_store.py`, `services/ppt_exporter.py`,
`services/ppt_style_extractor.py`.

**Endpoints (`/ppt-store`):** `GET /templates`, `POST /templates/upload`,
`DELETE /templates/{filename}`, `POST /export`, `GET /reports`, `DELETE /reports/{filename}`.
Also `POST /results/export-ppt`.

**Generation (`ppt_exporter.generate_ppt_report(ids)`):**
- Loads `ScreenshotResult` rows (scanner_db).
- Base template from `PPT_Format/` (e.g. `CA01437_Banoffee_..._Apr'26.pptx`).
- Desktop screenshots → Layout 0 (one image/slide); Mobile → Layout 5 (two/slide).
- `ppt_style_extractor` reads theme colors/fonts/assets from the template.
- Returns a `BytesIO` `.pptx`; saved under `ppt_reports/`.

---

## 3. Authentication & User Management

**Files:** `routers/auth.py`, `routers/users.py`, `core/security.py`, `core/deps.py`,
`core/auth.py`, `models/user.py` (all users live in **ctr_db**).

**Auth model [CONFIRMED]**
- JWT (HS256), secret from `JWT_SECRET` env (⚠️ default placeholder if unset),
  expiry `ACCESS_TOKEN_EXPIRE_MINUTES` (default 480 = 8h).
- Passwords hashed with **bcrypt**; login runs bcrypt in a thread pool.
- Two roles: `super_admin` (all pages + user management) and `admin`
  (restricted to `allowed_pages`).
- Page keys: `scanner` (index.html), `crm_excel` (crm-excel.html),
  `ppt_store` (ppt-store.html), `final_report` (final-report.html).
  `allowed_pages = None` means all pages (super_admin).

**Endpoints**
- `POST /auth/login` (form username/password → JWT + role + allowed_pages),
  `GET /auth/me`, `POST /auth/logout`.
- `/users/` CRUD — **super_admin only** (`require_super_admin`): list, create, get,
  `PATCH` role/status, `DELETE` (deactivate).

**Guards (`core/`)**
- `core/deps.py`: `get_current_user`, `require_admin`, `require_super_admin` (JWT-based, preferred).
- `core/auth.py`: `require_api_key` (legacy header/API-key guard used by scanner/creatives/utilities).

> **Two distinct auth mechanisms coexist:** JWT role guards (auth/users/final-report
> UI flows) and the simpler `require_api_key` (scanner, creatives, ppt-store, results,
> utilities). [CONFIRMED]

---

## 4. Utilities & System

**File:** `routers/utilities.py`.

| Endpoint | Purpose |
|----------|---------|
| `POST /convert/excel-to-csv` | Convert uploaded Excel → CSV. |
| `GET /health`, `GET /ping` | Liveness. |
| `GET /get-image-base64?path=` | Return an image as base64 (api-key). |
| `GET /ppt-export-assets` | Return PPT asset images. |
| `GET /api/vpn/status`, `POST /api/vpn/toggle` | VPN status/toggle helpers. |

Helpers: `_hex_clean`, `_blend` (gradient color blending).

---

## 5. Standalone maintenance scripts (repository root)

Not part of the running app — one-off migration/admin tools run manually:
- DB migration: `migrate_to_render.py`, `migrate_users_to_railway.py`,
  `migrate_city_db.py`, `migrate_city_reference_to_railway.py`,
  `migrate_app_url_db.py`, `rebuild_app_url_reference.py`, `setup_railway_db.py`,
  `reference_db_city_patch.py`.
- User admin: `create_qc_user.py`, `create_railway_user.py`, `reset_passwords.py`,
  `reset_railway_passwords.py`, `restore_permissions.py`, `fix_admin_pages.py`.
- Data patches: `add_priority_column.py`, `update_app_urls.py`,
  `fix_render_sequences.py`, `verify_railway_db.py`.
- `Backend_Screenshot/scripts/` — DB/table creation + test scripts
  (`create_tables.py`, `create_super_admin.py`, `seed_from_screenshots.py`, tests).
- `src/ad_placer.py` (repo root) — a separate/legacy ad-placement script. [INFERRED]

See `FILE_DOCUMENTATION/FILE_REFERENCE.md` for the complete list.
