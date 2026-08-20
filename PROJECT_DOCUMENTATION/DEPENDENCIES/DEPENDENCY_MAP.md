# Dependency Map

## Module → file dependency chains

### CRM Excel Generator
```
crm-excel.html
  → routers/crm.py
       → schemas/crm.py            (request validation)
       → models/crm.py            (ctr_db ORM)
       → database/crm_db.py        (get_crm_db)
       → services/crm_memory.py    (yesterday_memory)
       → services/crm_processor.py (process_rows, OUTPUT_COLUMNS)  ← CORE
       → services/crm_excel_writer.py (build_excel — available, not on /process path)
       → pandas, openpyxl
```

### Reach Report Generator
```
reach-report.html
  → routers/reach_report.py
       → services/reach_parser.py     (parse_campaign_file, parse_template_file, parse_filename)
       → services/reach_generator.py  (generate_reach_report → _Generator)  ← CORE
       → ctr_db.reach_report_store    (raw psycopg2 SQL)
       → openpyxl
```

### Final Report Generator
```
final-report.html / qc-checker.html
  → routers/final_report.py
       → services/excel_splitter.py   (split_excel_to_files)         ← STEP 1
       → services/report_generator.py (generate_report + build_sheet1..10) ← STEP 2 CORE
            → database/crm_db.py :: crm_engine (raw connection)
            → ctr_db.app_url_reference, ctr_db.city_reference (raw SQL)
       → ctr_db.final_report_store    (raw SQL, RETURNING id)
       → (internal) QC engine: _run_*_qc, _auto_correct_report
       → pandas, openpyxl
```

### Scanner
```
index.html
  → routers/scan.py
       → services/browser.py                 ← ORCHESTRATOR
            → services/ad_detector.py         (DOM detection)
            → services/vision_detector.py     (Claude Vision, optional)
            → services/smart_placement.py     (fallback placement)
            → services/image_utils.py         (creative match/resize, site_creatives.json)
            → services/ppt_style_extractor.py (styles)
            → services/db_service.py          (scanner_db.screenshot_results)
            → services/screenshot_storage.py  (ctr_db.scan_screenshots)
       → playwright, playwright-stealth, PIL
```

### PPT / Results
```
ppt-store.html / results
  → routers/ppt_store.py, routers/results.py
       → services/ppt_exporter.py       (generate_ppt_report)
            → services/ppt_style_extractor.py
            → database/db.py :: SessionLocal (scanner_db)
            → models/screenshot.py
       → python-pptx, PIL
```

### Auth
```
login.html / all gated pages
  → routers/auth.py, routers/users.py
       → core/security.py (JWT + bcrypt)
       → core/deps.py / core/auth.py (guards)
       → models/user.py → database/crm_db.py (ctr_db)
```

## Shared components (used across modules)

| Shared thing | Used by | Notes |
|--------------|---------|-------|
| `core/config.py` `Settings` | everything | Single source of env config |
| `core/paths.py` | main, routers, services | Resolved dirs |
| `database/crm_db.py` (ctr_db) | crm, reach, final, users, scan_screenshots | **Critical** — most tables here |
| `database/db.py` (scanner_db) | scanner, ppt_exporter | screenshot_results only |
| `core/security.py` / `deps.py` / `auth.py` | auth + gated routes | Two auth mechanisms (JWT + api-key) |
| `services/ppt_style_extractor.py` | browser (scan) + ppt_exporter | Template styling |
| `pandas` + `openpyxl` | crm, final, utilities | Excel/CSV backbone |
| `site_creatives.json` | image_utils (scanner) | Site→creative mapping |
| `ctr_db.app_url_reference` / `city_reference` | final_report | Reference data (populated by root scripts) |

## External dependencies

| External | Used by | Required? |
|----------|---------|-----------|
| PostgreSQL (prod) / SQLite (dev) | all DB access | Yes |
| Playwright + Chromium | scanner | Yes for scanning |
| Anthropic Claude Vision API | vision_detector, smart_placement | Optional (graceful fallback) |
| Target websites | scanner | Yes for scanning |
| Netlify (frontend host) / Render / Railway (backend) | deployment | Deployment-specific |

## Critical dependencies (do NOT break without understanding)

1. **`ctr_db` (`database/crm_db.py`)** — powers users, CRM, reach store, final store, and
   the two reference tables. A wrong `CRM_DATABASE_URL` silently degrades reports.
2. **`services/crm_processor.py :: OUTPUT_COLUMNS`** — shared by the processor, the Excel
   writer, and the router's CSV builder. Changing it in one place breaks the others.
3. **`services/report_generator.py`** — the sheet builders + sanitizers are tightly coupled;
   Grand-Total literals are relied on by the QC engine.
4. **`app_url_reference` / `city_reference` schema** — queried by exact column names in
   raw SQL; renaming a column breaks `get_urls_from_sheets` / `load_city_db_sheet`.
5. **`models/screenshot.py` columns** — the startup `ALTER TABLE` guard adds specific
   columns by name; both must stay in sync.
6. **Reach `REQUIRED_SHEETS`** — parser hard-requires all 10 sheet names.

## Circular/coupling notes
- `crm_excel_writer.py` imports `OUTPUT_COLUMNS` from `crm_processor.py` (one-way).
- `browser.py` imports many sibling services — it is the scanner's hub; changes there ripple.
- Routers import services but services (except report_generator/screenshot_storage/db_service)
  avoid importing routers — the layering is mostly clean.
