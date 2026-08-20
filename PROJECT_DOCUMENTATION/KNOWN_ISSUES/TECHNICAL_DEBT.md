# Known Issues & Technical Debt

Findings from reading the code. **No code was modified.** Severity is the author's
assessment for maintainability/risk.

## Critical

1. **Default super_admin credentials (`admin` / `admin123`).**
   `main.py` startup auto-creates this if `users` is empty. If reachable in production
   this is a full-access backdoor. → Rotate immediately; gate creation behind an env flag.

2. **Default JWT secret placeholder.**
   `core/security.py` uses `"change-me-in-production-supersecret-key"` if `JWT_SECRET`
   is unset. It only **warns** in production (does not refuse to start). Anyone knowing
   the default can forge tokens. → Fail hard when default is used with `APP_ENV=production`.

3. **Data fabrication is invisible to end users.**
   Final Report invents totals (`randint(150_000, 300_000)`) and all breakdowns when input
   is sparse; CRM/Reach synthesize clicks/reach. There is no on-report marker that numbers
   are generated. → Business/compliance risk; consider a provenance flag. (This is core
   product behavior, not a bug — but must be understood before changing ranges.)

## High

4. **Two overlapping auth systems.** JWT role guards (`core/deps`) and `require_api_key`
   (`core/auth`) protect different routes. Scanner-family endpoints use only the API key
   (which defaults to disabled). Easy to leave endpoints unprotected. → Consolidate.

5. **Schema drift between Alembic and runtime.** The app relies on `create_all()` + ad-hoc
   `ALTER TABLE ... ADD COLUMN` guards in `main.py` rather than Alembic migrations, which
   also exist. Two sources of truth for schema. → Pick one (prefer Alembic).

6. **Raw SQL tables not modeled.** `final_report_store`, `reach_report_store`,
   `app_url_reference`, `city_reference` are created/queried with hand-written SQL scattered
   across routers/services and root scripts. No ORM, no single schema definition. → Fragile
   to column renames; centralize.

7. **`RETURNING id` portability.** `_save_report_to_db` uses PostgreSQL `RETURNING` — not
   portable to SQLite. Local-dev final-report saving may fail (swallowed as a warning,
   yielding `report_id=None` and skipped QC persistence).

8. **CORS defaults to allow-all.** `ALLOWED_ORIGINS` empty → `["*"]`. Combined with the
   weak API-key default, this is permissive by default. → Set explicit origins in prod.

## Medium

9. **CRM `/process` emits CSV, but `build_excel` exists and is imported unused on that path.**
   Naming ("Excel Generator") vs behavior (CSV) mismatch; dead-ish code. → Clarify intent.

10. **Unseeded randomness in CRM & Final Report.** Output differs every run; hard to test or
    reproduce a specific report. → Optional seed parameter for reproducibility.

11. **Reach Report Booked Impressions never populated.** `parse_template_file` stubs booked
    impressions (`pass`), so Overview Booked Impressions is 0 and pacing formulas divide by
    (0 − end). → Implement template parsing or remove the pacing formulas.

12. **Massive committed binary/output data.** `final_report_outputs/`,
    `reach_report_outputs/_uploads/`, `screenshots/` (hundreds of PNGs), `processed_outputs/`,
    DB dumps (`*.sql`, `*.dump`), and `scanner.db` are in the repo. Bloats clone size and may
    leak client data. → `.gitignore` outputs; purge history if sensitive.

13. **Pervasive silent-failure `except Exception` blocks.** Especially DB reads and Excel
    formatting. Masks real misconfiguration. → Log at higher severity or surface to the user.

14. **Duplicated helper logic.** `safe_int`/`safe_float`/`_rescale_to_total`/ad-type detection
    exist in multiple files (`crm_processor`, `report_generator`, `final_report`). → Extract shared utils.

15. **`_detect_ad_type` keyword lists duplicated** in `routers/crm.py` and
    `routers/final_report.py` with slightly different sets. → Single source.

## Low

16. **Misspelled data filenames** (`Fianl Site for automation...`). Cosmetic but referenced
    by scripts — renaming requires updating the scripts.
17. **`print()` used for DB errors** in `report_generator.py` instead of the logger.
18. **Hardcoded backend URL** in `netlify.toml` (`creative-scanner-backend-2.onrender.com`)
    and hardcoded `http://127.0.0.1:8001` fallbacks across HTML files.
19. **`src/ad_placer.py`** at repo root looks like a legacy/standalone script not wired into
    the app. → Confirm and remove if dead.
20. **Multiple pre-existing analysis docs** (`project_analysis*.md`, `ARCHITECTURE.md`, etc.)
    may be stale and contradict the code. → This folder supersedes them.
21. **`@app.on_event("startup")`** is a deprecated FastAPI hook (lifespan handlers preferred).
22. **Windows-specific `.bat` launchers** and browser-profile dirs (`browser_data*/`) committed.

## Performance / scalability notes
- QC on final reports is heavy; a full second QC pass is deliberately skipped to save 60–90s.
- Scanner concurrency is memory-bound (`ENGINE_CONCURRENCY`); wrong value OOMs on small hosts.
- Storing screenshot binaries in `ctr_db` (BYTEA) grows the DB quickly.
- Reference-table reads happen per report generation (no caching layer).
