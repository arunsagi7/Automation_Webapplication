# Error Handling

## General patterns [CONFIRMED]

- **Routers** raise `HTTPException` with appropriate status codes for user-facing
  errors (400 bad file/type, 404 not found, 422 bad JSON, 500 processing error) and
  log with `logger.exception(...)` for stack traces.
- **Services** tend to fail soft: DB helper functions catch exceptions, `rollback()`
  the session, log a warning, and return an empty/default result so the request can
  continue. This means **missing reference data degrades silently** rather than erroring.
- **Sessions** use try/except/rollback/finally (`get_db`, `get_crm_db`). Several places
  call `db.rollback()` defensively before a write to clear a stale read-transaction.

## Module-specific

### CRM (`routers/crm.py`, `services/crm_*`)
- Extension not in `{xlsx,xls,csv}` → 400.
- Bad `rules`/`settings` JSON → 422.
- Unreadable file → 400; empty file → 400.
- `process_rows` failure on a sheet → 500 (`logger.exception`).
- Disk save failure → logged warning, continues (DB record still written).
- `processed_files` unique-constraint clash → caught `IntegrityError`, updates existing row.
- `load_yesterday_memory` / `_load_db_rules` / `_load_global_settings` failures →
  rollback + warning + fall back to defaults (processing still runs).
- `save_today_snapshot` failure → warning only (memory just not updated).

### Reach Report (`routers/reach_report.py`, `reach_parser.py`)
- Non-`.xlsx` upload → collected into `errors[]` (not fatal).
- Missing required sheet → `ValueError` → 400 with the offending file name.
- Template/campaign parse error → 400.
- Workbook generation error → 500 (`logger.exception`).
- DB history save failure → warning only (file still returned to user).

### Final Report (`routers/final_report.py`, `report_generator.py`, `excel_splitter.py`)
- Split with no data → `ValueError("No data found...")` → 400.
- Unsupported file type → 400.
- `generate_report` `ValueError` (e.g. empty campaign file) → 400; other errors → 500.
- **Auto-QC is wrapped in try/except** — if QC fails, the report is still saved and
  returned; only a warning is logged ("Auto-QC failed (report still saved)").
- Reference table reads (`get_urls_from_sheets`, `load_city_db_sheet`) catch all
  exceptions and return `[]` → CITY/APP URL sheets fall back to empty/default.
- DB store/update failures → warnings; the file itself is not lost (returned in-memory).

### Scanner (`routers/scan.py`, `services/browser.py`)
- No valid URLs → 400 JSON.
- Per-URL errors are captured and emitted as scan events (`site_*` / `error`) rather than
  failing the whole batch; navigation uses `_navigate_with_retry` with a commit-level fallback.
- Background scan task exceptions are surfaced into the NDJSON stream as `{"type":"error"}`.
- Vision detection failures return `[]` (graceful — see `vision_detector` docstring).

### Auth (`routers/auth.py`, `core/`)
- Wrong username/inactive user/bad password → 401 (`WWW-Authenticate: Bearer`).
- bcrypt runs in a thread pool so a slow hash never blocks the event loop.
- Invalid/expired JWT → handled in `core/deps.get_current_user` (401).

## Retry / fallback logic
- **Scanner navigation:** retry with commit-level fallback (`_navigate_with_retry`).
- **CRM generation:** up to 150 re-roll attempts for de-duplication, then relaxed fallback.
- **Slot detection:** three-tier fallback (DOM → Vision → smart placement).
- **Startup migrations:** each `ALTER TABLE` wrapped in try/except + rollback (idempotent).
- **`final_report_store` DDL:** PostgreSQL `IF NOT EXISTS`, with a SQLite `ADD COLUMN` fallback.

## Logging
- Configured centrally by `core/logging.py :: configure_logging()`; level from `LOG_LEVEL`.
- `backend_log.txt` present in the backend dir (runtime log). `migration_log.txt` at root.

## Weak spots / missing handling [INFERRED]
- **Silent degradation** is the dominant pattern: when a DB read fails, generators keep
  going with empty/random data. A wrong `CRM_DATABASE_URL` may produce plausible-but-empty
  reports instead of a clear error.
- **`RETURNING id`** in `_save_report_to_db` is PostgreSQL-specific — on SQLite this path
  may raise/behave differently. Wrapped in try/except at the call site (warning only), so a
  failure yields `report_id=None` and the QC-update step is skipped.
- Many `except Exception: pass` blocks in Excel-writing helpers swallow formatting errors.
- Disk writes to output dirs assume the directory exists / is writable (created at startup,
  but a read-only FS on some PaaS ephemeral disks would lose files silently).
- No global exception middleware — unhandled errors return FastAPI's default 500.
