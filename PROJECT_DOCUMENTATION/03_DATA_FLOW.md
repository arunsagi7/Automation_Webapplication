# 03 — End-to-End Data Flow

Each module is an **independent pipeline**. They do **not** chain into one another
(the CRM output is not fed into the Reach generator, etc.) — the "CRM → Reach →
Final" ordering in the original request prompt is **not** how the code works.
[CONFIRMED — verified by tracing imports; no module imports another module's output.]

What they share: the same **`ctr_db`** database, the same **auth layer**, the same
**frontend shell**, and the same **synthesize-then-format** philosophy.

---

## Flow A — CRM Excel Generator

```
crm-excel.html
  │  POST /crm/process   (multipart: file, rules JSON, settings JSON)
  ▼
routers/crm.py :: crm_process()
  1. Parse rules[] and settings{} from form
  2. _load_db_rules(db)          ← ctr_db.campaign_rules (enabled only)
  3. _load_global_settings(db)   ← ctr_db.global_settings (id row)
  4. _merge_form_rules()         ← form rules OVERRIDE db rules
  5. load_yesterday_memory(db)   ← ctr_db.yesterday_memory
  6. _read_file() → {sheet_name: [row dicts]}  (pandas, all sheets)
  ▼  for each sheet:
services/crm_processor.py :: process_rows(rows, yesterday_memory, min, max, rules)
     Step 0  normalize Date → DD/MM/YYYY
     Step 1  generate Clicks + CTR within [min,max] avoiding yesterday's values
     Step 2  de-duplicate clicks/CTR within each Line Item group
     Step 3  generate VCR (Start/Complete Views) + Viewability within ranges,
             enforcing impression-gap rules
     Step 4  compute "For Checking" columns, project to OUTPUT_COLUMNS
     → (output_rows, today_snapshot)
  ▼
routers/crm.py (cont.)
  7. Build CSV per sheet (pandas → OUTPUT_COLUMNS order)
  8. Save CSV to processed_outputs/ on disk
  9. Log row to ctr_db.processed_files (with ad_type Video/Banner)
 10. save_today_snapshot(db, merged)  → REPLACE ctr_db.yesterday_memory
  ▼
Response: single sheet → stream .csv;  multiple sheets → .zip of CSVs
```

> Note: despite the name "Excel Generator", the default `/crm/process` output is
> **CSV** (or a zip of CSVs). `services/crm_excel_writer.py :: build_excel()` produces
> a styled `.xlsx` and is imported, but the `/process` endpoint currently emits CSV.
> [CONFIRMED — `crm_process` builds `df.to_csv`; `build_excel` is available but not
> called by `/process`.] See `KNOWN_ISSUES`.

---

## Flow B — Reach Report Generator

```
reach-report.html
  │  (1) POST /reach-report/upload   (multipart: files[])
  ▼
routers/reach_report.py :: upload_files()
     - Save each .xlsx to reach_report_outputs/_uploads/ with uuid prefix
     - File whose name contains "template" → template; others → campaign inputs
     - For inputs: parse_filename() → (audience, burst)
     → returns { template:{path}, inputs:[{path,audience,burst}], errors[] }
  │
  │  (2) POST /reach-report/generate  (form: template_path, input_paths CSV,
  │                                    platform, format_type, output_label)
  ▼
routers/reach_report.py :: generate_report()
     for each input path:
        services/reach_parser.py :: parse_campaign_file(path)
            - Requires 10 sheets (REACH/DATE/APP URL/TIME OF DAY/EXCHANGE/
              DEVICE/CREATIVE/CITY/AGE/GENDER)
            - _parse_reach_sheet → impressions, clicks, ctr, reach, frequency
            - _parse_date_sheet → start/end dates, complete views, VCR
            - device/creative/age/gender breakdowns
            → CampaignData
     parse_template_file(template_path, platform, format_type) → TemplateMetadata
     ▼
services/reach_generator.py :: generate_reach_report(campaigns, template)
     - _sort_campaigns() by canonical audience/burst order
     - Write "Overview" section (1 row per campaign, with Excel formulas)
     - Write per-campaign "Performance breakdown" sections
       (By Device / Creative / Age / Gender), allocating reach + complete
       views proportionally via _allocate_reach()
     → openpyxl Workbook (single sheet "MPN & CPN Breakdown")
     ▼
  - Serialize to bytes, INSERT into ctr_db.reach_report_store (raw SQL)
Response: .xlsx download
```

---

## Flow C — Final Report Generator (two-step: split → generate)

```
final-report.html
  │  (1) POST /final-report/process   (multipart: file)
  ▼
routers/final_report.py :: final_report_process()
services/excel_splitter.py :: split_excel_to_files(bytes, filename)
     - collect_blocks(): detect data "boxes" within each worksheet
       (a single sheet can contain many independent tables/boxes)
     - determine_sheet_name(): Format A (Line Item column) or Format B (box B1 label)
     - Emit ONE single-sheet .xlsx per block → saved to final_report_outputs/
     - _detect_ad_type(): name keywords first, then column-header scan → Video/Banner
     → returns [{name, filename, ad_type}, ...]
  │
  │  (2) POST /final-report/generate  (form: filename, languages, cities,
  │                                    app_urls, mode; optional file2 w/ Creative col)
  ▼
routers/final_report.py :: generate_final_report()
services/report_generator.py :: generate_report(...)
     - _parse_banner_format() OR pandas read → total_imp, total_clk
     - build_sheet1_reach ... build_sheet10_apps  (synthesize each breakdown)
     - _sanitize_sheet_data() per sheet (fix sums, cap CTR ≤ 0.90%)
     - _pre_write_qc_fix() cross-sheet Grand-Total consistency
     - Reference data: get_urls_from_sheets() ← app_url_reference,
                       load_city_db_sheet()   ← city_reference   (ctr_db, raw SQL)
     - write_*_sheet(): styled 10-sheet workbook
     → report bytes
     ▼
  - _save_report_to_db() → INSERT ctr_db.final_report_store, get report_id
  - Auto-QC: read REACH values, _run_all_qc(), _auto_correct_report()
  - UPDATE final_report_store with qc_status/qc_results/corrected file
Response JSON: { report_id, filename, qc_status, qc_results, corrections }
Frontend then GET /final-report/reports/{id}/download
```

`qc-checker.html` is a separate front-end surface for the QC results and the
`/final-report/reports/{id}/send-to-qc`, `.../qc-report/download`, `.../reach-data`
endpoints.

---

## Flow D — Creative Scanner

```
index.html
  │  POST /process   (JSON/form/query: urls[], device)   [require_api_key]
  ▼
routers/scan.py :: process_urls()
     - _normalize_urls(), device = desktop|mobile
     - Launch services.browser.open_website(urls, emit_cb, device) as a task
     - Stream NDJSON events (started → site_* → match_* → finished/error)
  ▼
services/browser.py :: open_website()
     Per URL (concurrency-limited by ENGINE_CONCURRENCY):
       1. Playwright launch + stealth + resource/ad blocking
       2. Navigate w/ retry; close popups/consent/overlays
       3. Detect ad slots:  ad_detector (DOM)  → vision_detector (Claude, optional)
                            → smart_placement (fallback)
       4. Match a local creative to each slot (image_utils.find_best_match,
          site_creatives.json mapping)
       5. Inject creative via page.evaluate JS overlay, screenshot
       6. Save PNG to screenshots/ + save_screenshot_result (scanner_db) +
          save_screenshot_to_db (ctr_db.scan_screenshots, with binary)
Response: application/x-ndjson stream
```

---

## Flow E — PPT export

```
ppt-store.html / index.html results
  │  POST /ppt-store/export  or  /results/export-ppt   (screenshot IDs)
  ▼
services/ppt_exporter.py :: generate_ppt_report(ids)
     - Loads ScreenshotResult rows (scanner_db)
     - Uses a base template .pptx (PPT_Format/) + ppt_style_extractor styles
     - Desktop → Layout 0 (1 img/slide); Mobile → Layout 5 (2 imgs/slide)
     → BytesIO .pptx  (saved to ppt_reports/)
```
