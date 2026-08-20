# Project Summary (Final)

## The system in one paragraph

**Creative Scanner Pro** is an internal FastAPI + vanilla-JS platform for a
multicultural advertising agency. It bundles five tools behind one backend and one
multi-page frontend: (1) a **CRM Excel Generator** that fabricates realistic,
de-duplicated Clicks/CTR/VCR/Viewability figures within configured ranges; (2) a
**Reach Report Generator** that consolidates per-audience "burst" campaign files into
one styled "MPN & CPN Breakdown" workbook; (3) a **Final Report Generator** that splits
a multi-block Excel and synthesizes a full 10-sheet campaign report with automated QC;
(4) a **Creative Scanner** that uses Playwright to screenshot live websites with the
client's ad creative injected into detected slots; and (5) a **PPT Store** that turns
those screenshots into PowerPoint decks. It runs on two isolated databases —
`scanner_db` (screenshots) and `ctr_db` (everything else) — defaulting to SQLite locally
and PostgreSQL in production (Render/Railway/Netlify). The defining characteristic of the
report tools is that they **synthesize plausible, internally-consistent data** from sparse
inputs using weighted-random, sum-preserving apportionment, then format it into
client-ready Excel.

## Module summary

| Module | Purpose | Input | Output | Main files |
|--------|---------|-------|--------|-----------|
| CRM Excel Generator | Generate realistic, de-duplicated metrics within ranges | `.xlsx/.xls/.csv` + rules + settings | `.csv` or `.zip` of CSVs | `routers/crm.py`, `services/crm_processor.py`, `crm_excel_writer.py`, `crm_memory.py` |
| Reach Report Generator | Merge burst files into one formatted workbook | Multiple campaign `.xlsx` + template | `.xlsx` ("MPN & CPN Breakdown") | `routers/reach_report.py`, `services/reach_parser.py`, `reach_generator.py` |
| Final Report Generator | Split + synthesize 10-sheet report + QC | `.xlsx` (multi-block) then a split file | Report `.xlsx` + QC JSON | `routers/final_report.py`, `services/excel_splitter.py`, `report_generator.py` |
| Creative Scanner | Screenshot sites with injected creatives | URLs + device | NDJSON stream + screenshots (disk + DB) | `routers/scan.py`, `services/browser.py`, `ad_detector.py`, `vision_detector.py`, `smart_placement.py`, `image_utils.py` |
| PPT Store | Build decks + manage templates | Screenshot IDs / templates | `.pptx` | `routers/ppt_store.py`, `routers/results.py`, `services/ppt_exporter.py`, `ppt_style_extractor.py` |
| Auth & Users | Login, JWT, role-based page access | credentials | JWT + user CRUD | `routers/auth.py`, `users.py`, `core/security.py`, `deps.py`, `models/user.py` |
| Utilities | Excel→CSV, health, image base64, VPN | various | various | `routers/utilities.py` |

## Critical components (do not modify without understanding dependencies)

1. `services/crm_processor.py :: OUTPUT_COLUMNS` — coupled to the Excel writer and the CSV builder.
2. `services/report_generator.py` sheet builders ↔ the QC engine in `routers/final_report.py`
   (Grand-Total rows are literals by contract so QC can read them).
3. `ctr_db` schema and the raw-SQL tables (`final_report_store`, `reach_report_store`,
   `app_url_reference`, `city_reference`) — queried by exact column names.
4. Reach `REQUIRED_SHEETS` and the position-dependent Excel formulas in the Overview section.
5. Auth: `JWT_SECRET`, roles/`allowed_pages`, and the coexisting JWT + API-key mechanisms.
6. Startup `ALTER TABLE` guards in `main.py` ↔ `models/screenshot.py` columns.

## Most important modification points

- **CRM Excel Generator:** `crm_processor.py` (`OUTPUT_COLUMNS`, `process_rows`),
  `crm_excel_writer.py` type sets, `routers/crm.py` rule merge + response.
- **Reach Report Generator:** `reach_parser.py` parsers; `reach_generator.py`
  (`_write_overview_row`, `_write_breakdown`, `_allocate_reach`, `_EXPECTED_ORDER`).
- **Final Report Generator:** `report_generator.py` (`generate_report`, `build_sheetN_*`,
  `write_*_sheet`, `_sanitize_sheet_data`), `excel_splitter.py`, QC in `final_report.py`.
- **Shared utilities:** `core/config.py`, `core/paths.py`, `database/crm_db.py`, and the
  duplicated `safe_int`/`safe_float`/ad-type helpers.
- **Data processing:** `_largest_remainder`, `_rescale_to_total`,
  `deduplicate_preserving_sum`, `_allocate_reach`.
- **Excel generation:** `write_*_sheet` + `_sh_*` (final), `_cell`/formats (reach),
  `crm_excel_writer` (crm).
- **DB/API integrations:** `database/crm_db.py`, raw-SQL in `final_report.py`/`reach_report.py`,
  reference loaders in `report_generator.py`.

## Questions / Unknowns (not determinable from source alone)

1. **Exact production schema of `app_url_reference` / `city_reference`** — inferred from the
   root migration scripts (`rebuild_app_url_reference.py`, `migrate_city_db.py`); the live
   production tables may differ if altered manually. [PARTIAL]
2. **Whether Alembic or the runtime `create_all`/`ALTER TABLE` guards is the intended source
   of truth.** Both exist. [UNKNOWN]
3. **Whether `crm_excel_writer.build_excel` is intended to replace the CSV output** on
   `/crm/process` (it's imported but unused there). [UNKNOWN]
4. **`src/ad_placer.py` (repo root)** — appears to be a legacy/standalone script; its current
   role is unclear. [UNKNOWN]
5. **Full internals of some large builders** (`build_sheet8_city`, `build_sheet9_creative`,
   `build_sheet10_apps`, and the ~2400-line `browser.py`) were read at the
   structure/signature level, not line-by-line for every branch. The behaviors documented are
   accurate at that level; some deep edge cases inside those functions were not exhaustively
   traced. [PARTIAL]
6. **The precise QC pass/fail thresholds** inside each `_run_*_qc` were catalogued by name and
   purpose, not every numeric threshold. [PARTIAL]
7. **Which deployment target is currently live** (Render vs Railway vs Hostinger) — configs
   for all three exist; `netlify.toml` points at a Render URL. [PARTIAL]
8. **Frontend behavior details** — the HTML pages were confirmed for their API calls and
   base-URL logic, but their full UI/UX flows were not exhaustively documented.

If any of these matters for a change you're making, open the referenced file and verify
against the live database before relying on the inference.
