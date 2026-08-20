# Excel Structure

Documents every Excel workbook the system generates or consumes.

---

## 1. CRM processed output

- **Filename:** `processed_{stem}.csv` (single sheet) or `processed_{stem}_{sheet}.csv`
  zipped as `processed_{stem}.zip` (multi-sheet). `crm_excel_writer.build_excel()` can
  produce a `.xlsx` with sheet **"Processed"** but the `/process` route emits CSV.
- **Sheet "Processed":** one header row + data rows, columns in `OUTPUT_COLUMNS` order.

| Column | Source | Transformation | Cell format (xlsx) |
|--------|--------|----------------|--------------------|
| Impressions, Billable Impressions, Clicks, Start Views, quartile views, Complete Views, Viewable/Measurable Impressions, For Checking, Start Views-Impression | input / generated | int | `INTEGER_COLS` → int |
| Click Rate (CTR), Video Completion Rate, Viewability | generated | value/100 | `PERCENT_COLS` → `"0.00%"` |
| Revenue (Adv Currency), Media Cost (Advertiser Currency) | input | float | `FLOAT_COLS` → float |
| All others (Advertiser, IDs, names, Date, Campaign) | input passthrough | string | text |

`build_excel` also appends `ignored_errors` (numberStoredAsText) over the data range.

---

## 2. Reach Report — "MPN & CPN Breakdown"

- **Filename:** `reach_report_{YYYYmmdd_HHMMSS}.xlsx`. **One sheet.**
- **Layout:** intro note (B2) → Overview section → per-campaign Performance sections.

### Overview section

Header (blue `0000FF`, white bold) at columns **B–S**:

| Col | Header | Source | Formula / Transformation | Format |
|-----|--------|--------|--------------------------|--------|
| B | Platform | template arg | — | text (bold) |
| C | Format | template arg | — | text |
| D | Audience | derived | `{audience} - {format} - Burst - {burst}` | text |
| E | Reporting Date | `datetime.now()` | — | `d"-"mmm` |
| F | Start Date | DATE sheet | min date | `d"-"mmm` |
| G | End Date | DATE sheet | max date | `d"-"mmm` |
| H | Booked Impressions | template dict | (currently 0 — not populated) | `#,##0` |
| I | Actual Impressions | REACH sheet | — | `#,##0` |
| J | Campaign Pacing | formula | `=(F-G)/(H-G)` | `0%` |
| K | Impression Pacing | formula | `=IFERROR(J/I,0)` | `0%` |
| L | Reach | REACH sheet | — | `#,##0` |
| M | Frequency | REACH sheet | default 3 | `#,##0` |
| N | Link Click | REACH sheet | — | `#,##0` |
| O | CTR | formula | `=N/I` | `0.00%` |
| P | Complete Views | DATE sheet | Σ or "-" | `#,##0` / — |
| Q | VCR | DATE sheet | Grand-Total ΣCV/ΣStarts or "-" | `0.00%` / — |
| R | Amount Spent | formula | `=S*L` | currency |
| S | Investment | manual | blank | currency |

### Performance breakdown (per campaign, per dimension)

Blue title, then yellow (`FFFF00`) sub-section headers **By Device / By Creative / By Age
/ By Gender**. Columns: label, Actual Impressions, Reach, Frequency (const 3),
Complete Views, Link Click, CTR (`=G/C` formula), Amount Spent ("-" for device/creative,
blank for age/gender). Reach + Complete Views allocated proportionally via `_allocate_reach`.

Column widths: A 4.73, B 55.09, C 14.73, D 27.09, E–S 14.0.

---

## 3. Final Report — 10-sheet campaign report

- **Filename:** `report_{stem}_{uid}.xlsx`. **Sheet creation order:**
  REACH, DATE, APP URL, TIME OF DAY, EXCHANGE, DEVICE, CREATIVE, CITY, AGE, GENDER.
- Each sheet: styled header row, data rows, a **Grand Total** row equal to the reference
  totals (literal values, not `=SUM()` — so QC/openpyxl can read them back).

| Sheet | Dimension column | Data source | Key transformation |
|-------|------------------|-------------|--------------------|
| REACH | (summary) | totals | Impressions, Clicks, CTR, Reach, Frequency |
| DATE | Date | input dates or synthetic 30-day | totals distributed per day (`_largest_remainder`) |
| APP URL | App/URL | `app_url_reference` + user URLs | tier-ordered URLs; per-row CTR ≤ 0.90% |
| TIME OF DAY | Hour | synthetic | split across hours |
| EXCHANGE | Exchange | synthetic (named list) | `split_across` names |
| DEVICE | Device | synthetic | split across device types |
| CREATIVE | Creative | `file2` / line-item tokens | per-creative split |
| CITY | City | `city_reference` (weighted) | weight-proportional (`_largest_remainder`) |
| AGE | Age band | synthetic | split across bands |
| GENDER | Gender | synthetic | split across Male/Female/(Unknown) |

**Sanitization applied to every sheet before write** (`_sanitize_sheet_data`): row
impressions rescaled to sum `total_imp`; clicks to `total_clk`; any row CTR capped at
**0.90%**; Grand-Total forced to reference values. Cross-sheet Grand-Total agreement
enforced by `_pre_write_qc_fix`.

**Number formats [INFERRED from `write_*_sheet` + `_sh_*` helpers]:** counts `#,##0`,
CTR `0.00%`, currency where applicable; header/total styled with fills + borders;
`_sh_suppress` adds numberStoredAsText ignoring.

---

## 4. Input formats consumed

- **CRM input:** DV360-style flat table (all sheets read). Columns per Data Dictionary.
- **Reach burst input:** 10 required sheets (REACH/DATE/APP URL/TIME OF DAY/EXCHANGE/
  DEVICE/CREATIVE/CITY/AGE/GENDER); only REACH/DATE/DEVICE/CREATIVE/AGE/GENDER parsed.
- **Final Report input:** arbitrary multi-block workbook. Two recognized block-naming
  formats — "Line Item" column (Format A) and box B1 label (Format B). Also a special
  "daily report"/box format (`_parse_banner_format`) where data may start at any column.
- **PPT template:** `.pptx` in `PPT_Format/` — cover slide + Layout 0 (desktop) + Layout 5 (mobile).

---

## 5. Reference/data files on disk

- `App_Url_Database.xlsx`, `Fianl Site for automation*.xlsx` (note the "Fianl" typo in
  filenames), `Fianl_Site_for_automation_standardized.xlsx` — source data for the
  `app_url_reference` table, loaded by root migration scripts.
- `final_report_outputs/`, `reach_report_outputs/_uploads/`, `processed_outputs/` —
  runtime outputs and uploads (many sample files present).
