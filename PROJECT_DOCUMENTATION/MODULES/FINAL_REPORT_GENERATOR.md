# MODULE — Final Report Generator

## Purpose

The most complex module. It does two things:

1. **Split** — takes a messy uploaded Excel that contains many independent data
   "blocks"/boxes (often one per line item or per campaign) and splits it into
   individual single-sheet `.xlsx` files (`excel_splitter.py`).
2. **Generate** — from one split file (which may contain little more than totals),
   **synthesizes a full 10-sheet campaign report** (REACH / DATE / APP URL /
   TIME OF DAY / EXCHANGE / DEVICE / CREATIVE / CITY / AGE / GENDER), runs
   **automated QC**, auto-corrects fixable failures, and stores it
   (`report_generator.py` + QC code in `routers/final_report.py`).

## Files involved

| File | Role |
|------|------|
| `routers/final_report.py` (2597 lines) | Endpoints, split orchestration, QC engine, auto-correction, `final_report_store` (raw SQL), reference-table endpoints, send-to-QC |
| `services/excel_splitter.py` | Detect blocks, name sheets, emit single-sheet files |
| `services/report_generator.py` (2180 lines) | Synthesize + write the 10-sheet workbook |

## Endpoints (`routers/final_report.py`, prefix `/final-report`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/final-report/process` | Upload `.xlsx/.xls`; split into blocks → list `[{name, filename, ad_type}]`. Saves each to `final_report_outputs/`. |
| POST | `/final-report/generate` | Form: `filename` (a split file), `languages`, `cities`, `app_urls`, `mode` (video/banner), optional `file2`. Generates + QC + stores. Returns JSON. |
| GET | `/final-report/languages` | Distinct `sheet_name` from `app_url_reference`. |
| GET | `/final-report/cities` | Distinct `sheet_name` from `city_reference` (ordered by Σ potential impressions). |
| GET | `/final-report/reports` | List saved reports. |
| GET | `/final-report/reports/{id}/download` | Download stored report. |
| DELETE | `/final-report/reports/{id}` | Delete a stored report. |
| POST | `/final-report/update-app-urls` | Upload a workbook to refresh `app_url_reference`. |
| GET | `/final-report/download?file=` | Download by filename from disk. |
| GET | `/final-report/reports/{id}/reach-data` | Read back REACH values for the QC UI. |
| POST | `/final-report/reports/{id}/send-to-qc` | Persist QC status/results. |
| GET | `/final-report/reports/{id}/qc-report/download` | Download the QC report. |

## STEP 1 — Splitting (`excel_splitter.py`)

`split_excel_to_files(file_bytes, filename) → [{sheet_name, raw_name, buf}]`

Pipeline:
1. `collect_blocks(wb)` — for each worksheet, `detect_boxes()` finds rectangular
   data regions separated by empty rows/columns. Whole-sheet tables become one block;
   multi-box sheets become several.
2. `determine_sheet_name(block) → (clean_name, raw_name)`:
   - **Format A** — if a `Line Item` header exists in the block's first row, use the
     value beneath it.
   - **Format B** — else use cell B1 of the box (first row, second col = box label).
   - Fallback — worksheet name, or `Sheet_N`.
   - `clean_name` is Excel-safe, truncated to 31 chars; `raw_name` is the full value.
3. `_unique_name()` de-duplicates tab names (`name_1`, `name_2`, …).
4. `_copy_block_to_sheet()` copies values + number formats + approximate column widths
   into a fresh single-sheet workbook per block.

`_detect_ad_type(name)` (name keywords) then `_detect_ad_type_from_buf(bytes)`
(column-header scan for video columns) classify each file **Video** or **Banner**.

## STEP 2 — Generation (`report_generator.py :: generate_report`)

Signature:
```python
generate_report(campaign_file_bytes, campaign_filename, language_sheet_names,
                city_sheet_names, user_urls_text="", mode="video",
                creative_file_bytes=None) -> bytes
```

**A. Determine base totals.**
- `_parse_banner_format()` first tries to detect a "daily report"/box-style layout
  (data may start at any column) → `(date_df, total_imp, total_clk, li_hint)`.
- Otherwise pandas reads the file (header row 0, retry row 1 if key cols missing).
- `total_imp`/`total_clk` = column sums. **If zero, they are randomly generated**:
  `total_imp = randint(150_000, 300_000)`, `total_clk = round(total_imp * rand(0.40%–0.55%))`.
- Video metric totals (Viewable/Measurable/Starts/Complete Views) captured if present.
- If no `Date` column, a **synthetic 30-day** date frame is created and totals are
  distributed across days via `_largest_remainder()`.

**B. Build each sheet** (`build_sheet1_reach` … `build_sheet10_apps`). Each returns
`(rows, total_row_dict)`. Breakdowns are synthesized with weighted random splits that
sum to the totals. Notable ones:
- `build_sheet2_date` — per-day impressions/clicks (+ video metrics for video mode).
- `build_sheet8_city` — pulls cities + weights from `city_reference` (`load_city_db_sheet`),
  distributes impressions by weight (`_largest_remainder`).
- `build_sheet9_creative` — uses the optional `file2` Creative column / line-item tokens.
- `build_sheet10_apps` — pulls URLs from `app_url_reference` (`get_urls_from_sheets`,
  priority-tiered) plus user-supplied URLs; caps per-row CTR ≤ 0.90%.

**C. Sanitize each sheet** (`_sanitize_sheet_data`):
- Step 1: rescale row impressions to sum exactly `total_imp`.
- Step 2: rescale clicks to sum exactly `total_clk`.
- Step 3: cap any row CTR at **0.90%** (`_SANITIZE_MAX_CTR = 0.009`), redistributing excess.
- Step 4: force Grand-Total dict to the reference totals (so the GT row is a literal, not a formula).

**D. Cross-sheet QC fix** (`_pre_write_qc_fix`) — ensures every sheet's Grand Total agrees
with the reference impressions/clicks/CTR before writing.

**E. Write workbook** — `write_reach_sheet`, `write_date_sheet`, …, `write_gender_sheet`.
Sheet creation order in the file: REACH, DATE, APP URL, TIME OF DAY, EXCHANGE, DEVICE,
CREATIVE, CITY, AGE, GENDER. Styled headers/totals, number formats, autofit, error suppression.

## STEP 3 — Automated QC (`routers/final_report.py`)

After generation the router:
1. Reads REACH values (Impressions, Clicks, CTR, Reach, Frequency) from the generated file.
2. `_run_all_qc(...)` runs the full battery:
   `_run_reach_qc`, `_run_date_qc`, `_run_campaign_qc`, `_run_app_url_qc`,
   `_run_exchange_qc`, `_run_device_qc`, `_run_city_qc`, `_run_creative_qc`,
   `_run_age_qc`, `_run_age_gender_qc`, `_run_time_of_day_qc`, and a cross-sheet
   Grand-Total check `_run_cross_sheet_gt_qc`.
3. `_auto_correct_report(file_bytes, qc_results)` fixes fixable FAILs (marks them
   `CORRECTED`) and returns corrected bytes.
4. Overall `qc_status`: `approved` (no fail/warn) / `warning` / `rejected` (fail, no
   corrections) / `warning` (fail but corrected).
5. Persists status + JSON results + (possibly corrected) file into `final_report_store`.

Response JSON: `{ success, report_id, filename, qc_status, qc_results, corrections }`.

## Reference data (both in `ctr_db`, raw SQL)

- **`app_url_reference`** `(sheet_name, url_id, url, priority)` — priority tiers
  `user_site > more_important > important > regular`. `get_urls_from_sheets()` returns
  URLs ordered by tier, shuffled within each tier. Built by root script
  `rebuild_app_url_reference.py` (boxes A-B=regular, E-F=important, I-J=more_important).
- **`city_reference`** `(sheet_name, city_name, potential_impressions, unique_cookies, …)`.
  `load_city_db_sheet()` returns `{name, weight}` (weight = potential_impressions ∥
  unique_cookies ∥ 1). Built by root scripts `migrate_city_db.py` / `reference_db_city_patch.py`.

## Math helpers worth knowing

| Function | Purpose |
|----------|---------|
| `_largest_remainder(weights, total_weight, total_count)` | Hamilton apportionment — distribute a count by weights, sum exact. |
| `_rescale_to_total(values, target)` | Rescale a list to sum exactly `target`. |
| `deduplicate_preserving_sum(values, gap)` | Make values distinct (≥gap apart) while keeping the sum. |
| `pct / safe_float / safe_int / serial_to_date / _clean_url` | Formatting + coercion. |

## Edge cases & known limitations

- **Fabricates totals** when the input has none (random 150k–300k impressions). Downstream
  numbers are entirely synthetic in that case. [CONFIRMED]
- `mode` (video/banner) is passed by the user and NOT auto-overridden even when a
  banner-format file is detected (box-format files can be either). [CONFIRMED]
- QC is heavy (full second pass avoided to save 60–90s). Auto-correction caps quality at
  "warning" when it had to fix FAILs.
- Reference tables must be pre-populated (via the root migration scripts) or CITY/APP URL
  sheets fall back to empty/defaults.
- Randomness largely **unseeded** → non-deterministic output across runs. [CONFIRMED]
- `final_report_store` uses `RETURNING id` (PostgreSQL syntax) in `_save_report_to_db` —
  correctness on SQLite is not guaranteed. [INFERRED — see KNOWN_ISSUES]
