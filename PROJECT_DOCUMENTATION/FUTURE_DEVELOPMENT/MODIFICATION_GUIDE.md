# Future Modification Guide

"If I need to change X, where do I look?" Use this with `MODULES/*.md` and
`DEPENDENCIES/DEPENDENCY_MAP.md`.

## Quick lookup table

| Requirement | Files / functions to modify | Dependencies to check | Risk |
|-------------|------------------------------|-----------------------|------|
| Add/rename a CRM output column | `services/crm_processor.py :: OUTPUT_COLUMNS` **and** the type sets in `services/crm_excel_writer.py` (INTEGER/FLOAT/PERCENT_COLS) **and** the router's `pd.DataFrame(..., columns=OUTPUT_COLUMNS)` | All three must agree | Medium |
| Change CRM CTR / VCR / viewability ranges | Defaults: `schemas/crm.py :: GlobalSettings`; per-rule: `campaign_rules` DB rows via `/crm/rules`; logic: `process_rows` Steps 1 & 3 | `global_settings` DB row overrides CTR | Low |
| Change CRM de-dup behavior | `process_rows` Step 2 (`_seq_gap`, retry loop), `crm_memory.save_today_snapshot` | yesterday_memory lifecycle | Medium |
| Change CRM gap rules | `get_gap_range`, `enforce_gap` in `crm_processor.py` | affects "For Checking"/"Start Views-Impression" | Low |
| Change CRM output to real Excel | Swap CSV build in `routers/crm.py :: crm_process` for `crm_excel_writer.build_excel` | response media type + multi-sheet zip | Medium |
| Modify Reach Overview columns/formulas | `services/reach_generator.py :: _write_overview_section` / `_write_overview_row` (headers + `values`/`fmts`) | Excel formula cell refs are position-dependent | Medium |
| Change Reach breakdown dimensions | `_write_performance_section` / `_write_breakdown` + parser (`reach_parser.py`) | needs matching source sheet parsing | Medium |
| Change Reach campaign ordering | `_EXPECTED_ORDER` in `reach_generator.py` | — | Low |
| Add a Reach source sheet to parse | Add `_parse_*_sheet` in `reach_parser.py`, a dataclass, wire into `parse_campaign_file`, render in generator | `REQUIRED_SHEETS` | Medium |
| Add a column to a Final Report sheet | `services/report_generator.py :: build_sheetN_*` (add key) **and** the matching `write_*_sheet` header/format | `_sanitize_sheet_data` keys, `_pre_write_qc_fix`, the QC `_run_*_qc` for that sheet | High |
| Change Final Report total fabrication | `generate_report` (`randint(150_000,300_000)`, CTR range) | downstream sheet sums | Medium |
| Change per-row CTR cap | `_SANITIZE_MAX_CTR` in `report_generator.py` (+ `build_sheet10_apps`) | QC `_run_*_qc` thresholds | Medium |
| Add a new data source (e.g. new reference table) | New raw-SQL loader in `report_generator.py` (like `get_urls_from_sheets`), a root migration script to populate it, wire into a `build_sheetN_*` | `crm_engine` connection, ctr_db schema | High |
| Change how a report is split | `services/excel_splitter.py :: detect_boxes` / `determine_sheet_name` | Format A/B detection, 31-char tab limit | High |
| Change Video/Banner detection | `routers/final_report.py :: _detect_ad_type` + `_detect_ad_type_from_buf` (and CRM's `_VIDEO_KEYWORDS`) | duplicated in two routers | Low |
| Modify QC rules / thresholds | `routers/final_report.py :: _run_*_qc`, `_run_all_qc`, `_auto_correct_report` | Grand-Total literals from generator | High |
| Change Excel output format/styling | `report_generator.py` `write_*_sheet` + `_sh_*` helpers; `reach_generator.py` `_cell`/`_blue_title`; `crm_excel_writer.py` | number-format strings | Medium |
| Add/modify an API endpoint | Relevant `routers/*.py`; register new router in `main.py` | auth guard choice (JWT vs api-key) | Medium |
| Change auth / roles / page access | `core/security.py`, `core/deps.py`, `models/user.py :: allowed_pages`, `routers/auth.py`/`users.py` | page keys mirrored in frontend | High |
| Add a scanner ad selector | `services/ad_detector.py :: CONFIG["selectors"]` | injection JS in `browser.py` | Medium |
| Change creative→site mapping | `site_creatives.json` + `services/image_utils.py` | — | Low |
| Change scanner concurrency/timeouts | env `ENGINE_CONCURRENCY`, `ENGINE_NAV_TIMEOUT_MS`; `browser.py` constants (`POST_MASK_WAIT_MS`) | host memory | Low |
| Change PPT layout | `services/ppt_exporter.py` (layout indices, `_add_desktop_slide`, `_add_mobile_slides`), base template in `PPT_Format/` | template slide layouts | Medium |
| Point frontend at a different backend | `Frontend_Screenshot/netlify.toml` proxy + `src/config/apiConfig.js` + per-page fallbacks | — | Low |
| Switch DB (SQLite↔Postgres) | env `DATABASE_URL` / `CRM_DATABASE_URL`; check `RETURNING id` and `IF NOT EXISTS` branches | raw-SQL portability | Medium |

## "Find where this happens" cheatsheet

| Question | Answer |
|----------|--------|
| Where are Clicks/CTR generated? | `services/crm_processor.py :: process_rows` Step 1 (+ Step 2 de-dup) |
| Where is VCR / Viewability generated? | `crm_processor.py :: process_rows` Step 3 |
| Why is a value "just below" impressions? | `get_gap_range` / `enforce_gap` (gap rules) |
| Where do report totals come from? | `report_generator.py :: generate_report` (input sums or random fallback) |
| Where are cities/URLs chosen? | `load_city_db_sheet` / `get_urls_from_sheets` (ctr_db reference tables) |
| Where is per-row CTR capped? | `_SANITIZE_MAX_CTR` = 0.009 in `report_generator.py` |
| Where is a report split into files? | `excel_splitter.py :: split_excel_to_files` |
| Where is QC run? | `routers/final_report.py :: _run_all_qc` + `_run_*_qc` |
| Where are reports stored? | ctr_db `final_report_store` / `reach_report_store`; CRM CSVs on disk in `processed_outputs/` |
| Where is yesterday's data remembered? | ctr_db `yesterday_memory` via `crm_memory.py` |
| Where does login happen? | `routers/auth.py :: login` → `core/security.py` |

## Most important modification points (by module)

- **CRM Excel Generator:** `crm_processor.py :: OUTPUT_COLUMNS`, `process_rows`;
  `crm_excel_writer.py` type sets; `routers/crm.py` rule merge + CSV/zip response.
- **Reach Report Generator:** `reach_parser.py` sheet parsers; `reach_generator.py`
  `_write_overview_row` + `_write_breakdown` + `_allocate_reach` + `_EXPECTED_ORDER`.
- **Final Report Generator:** `report_generator.py` `build_sheetN_*` + `write_*_sheet` +
  `_sanitize_sheet_data` + `_pre_write_qc_fix`; `excel_splitter.py` block detection;
  `final_report.py` QC + auto-correct.
- **Shared utilities:** `core/config.py`, `core/paths.py`, `database/crm_db.py`,
  duplicated `safe_int`/`safe_float`/ad-type helpers.
- **Data processing:** the apportionment functions `_largest_remainder`,
  `_rescale_to_total`, `deduplicate_preserving_sum`, `_allocate_reach`.
- **Excel generation:** `write_*_sheet` + `_sh_*` (final), `_cell`/number-format constants (reach),
  `crm_excel_writer` (crm).
- **DB/API integrations:** `database/crm_db.py` (ctr_db), raw-SQL blocks in
  `final_report.py`/`reach_report.py`, reference-table loaders in `report_generator.py`.

## Critical components — change only with full understanding
1. `OUTPUT_COLUMNS` (CRM) — 3-way coupling.
2. `report_generator.py` sheet builders ↔ QC engine (Grand-Total literals contract).
3. `ctr_db` schema + raw-SQL table column names.
4. Reach `REQUIRED_SHEETS` and Overview formula cell references.
5. Auth: JWT secret, role/`allowed_pages`, and the two auth mechanisms.
6. Startup `ALTER TABLE` guards ↔ `models/screenshot.py` columns.
