# MODULE — Reach Report Generator

## Purpose

Consolidates several per-audience **campaign "burst" files** (each a full
10-sheet campaign export) plus a **master template file** into a single formatted
Excel workbook named **"MPN & CPN Breakdown"**. The output has an **Overview**
section (one row per campaign) and a **Performance breakdown** section per campaign
(By Device / Creative / Age / Gender), styled to match the client's template
(blue headers, yellow sub-sections, specific number formats).

## Files involved

| File | Role |
|------|------|
| `routers/reach_report.py` | Endpoints, upload handling, `reach_report_store` (raw SQL) |
| `services/reach_parser.py` | Parse burst files + template → dataclasses |
| `services/reach_generator.py` | Build the styled openpyxl workbook |

## Endpoints (`routers/reach_report.py`, prefix `/reach-report`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/reach-report/upload` | Upload `.xlsx` files. `template` in name → template; others → inputs (parsed for audience/burst). Saves to `reach_report_outputs/_uploads/` with uuid prefix. |
| POST | `/reach-report/generate` | Form: `template_path`, `input_paths` (comma-sep), `platform` (MPN), `format_type` (Banner), `output_label`. Parses, generates, saves to DB, returns `.xlsx`. |
| GET | `/reach-report/history` | List saved reports. |
| GET | `/reach-report/history/{report_id}/download` | Download a saved report. |
| DELETE | `/reach-report/history/{report_id}` | Delete a saved report. |

## What triggers it

Manual — the user uploads files on `reach-report.html`, picks platform/format, then
clicks generate. There are **no scheduled jobs**. [CONFIRMED]

## Inputs

**Campaign burst file** (one per audience/burst). Must contain all 10 `REQUIRED_SHEETS`:
`REACH, DATE, APP URL, TIME OF DAY, EXCHANGE, DEVICE, CREATIVE, CITY, AGE, GENDER`
(missing any → `ValueError`). Only a subset are actually parsed for data (see below).

**Template file** — any `.xlsx` whose filename contains "template". Currently the
template only supplies `platform`/`format_type` (passed from the UI); booked-impression
parsing from the `"MPN & CPN Breakdown"` sheet is stubbed (a `pass` placeholder). [CONFIRMED]

**Filename parsing (`parse_filename`)** extracts `(audience, burst_number)`:
- Matches against `_AUDIENCE_KEYWORDS` (Vietnamese, Punjabi, Arabic, Chinese, Korean,
  Hindi, Tamil, Cantonese, … ~50 languages).
- Fallbacks: word before "burst"; else strip metadata tags (CA-codes, states, "final
  report", etc.) and take the first ≥3-letter word; else "General".
- Burst: `burst[_\-\s]*(\d+)`; fallbacks to a parenthesized/underscored number, else "1".

## What each source sheet contributes (`reach_parser.py`)

| Sheet | Parsed by | Data used |
|-------|-----------|-----------|
| REACH | `_parse_reach_sheet` | Row 2: impressions, clicks, ctr, reach, frequency (freq defaults 3.0). |
| DATE | `_parse_date_sheet` | Min/max date; sums Complete Views + Starts; recomputes Grand-Total VCR = ΣCV/ΣStarts (None if no VCR column → renders "-"). |
| DEVICE | `_parse_device_sheet` | Rows until blank; `DEVICE_MAPPING` normalizes labels; skips "grand total". |
| CREATIVE | `_parse_creative_sheet` | Name/impressions/clicks/ctr per creative. |
| AGE | `_parse_age_sheet` | Canonical band order `18-24 … 65+`; extra bands appended. |
| GENDER | `_parse_gender_sheet` | Male/Female/Unknown order; extras appended. |

APP URL / TIME OF DAY / EXCHANGE / CITY sheets are **required to exist but not parsed**
into the output. [CONFIRMED]

## Output structure (`reach_generator.py`)

Single sheet **"MPN & CPN Breakdown"**. Built by the internal `_Generator` class:

1. `_write_intro()` — a note at B2.
2. `_write_overview_section()` — blue "Overview" title; header row of 18 columns
   (Platform … Investment); one `_write_overview_row()` per campaign.
3. Per campaign: `_write_performance_section()` — blue title, then four
   `_write_breakdown()` yellow sub-sections (By Device, By Creative, By Age, By Gender).

**Overview columns (B–S):** Platform, Format, Audience (label
`{audience} - {format} - Burst - {burst}`), Reporting Date (now), Start Date, End Date,
Booked Impressions, Actual Impressions, Campaign Pacing (**Excel formula**
`=(F-G)/(H-G)`), Impression Pacing (`=IFERROR(J/I,0)`), Reach, Frequency, Link Click,
CTR (`=N/I`), Complete Views, VCR, Amount Spent (`=S*L`), Investment (manual, blank).

**Breakdown columns:** label, Actual Impressions, Reach, Frequency (const 3),
Complete Views, Link Click, CTR (`=G/C`), Amount Spent ("-" for device/creative, blank for age/gender).

## Key generation logic

- **`_sort_campaigns()`** — orders campaigns by `_EXPECTED_ORDER` (a hardcoded
  audience/burst sequence: Vietnamese/Punjabi bursts 1–3, then Arabic, Chinese, Korean,
  Hindi). Unlisted campaigns go last.
- **`_allocate_reach(total, impressions, seed)`** — distributes a total (reach or
  complete views) across breakdown rows **proportionally to impressions**, with slight
  seeded random noise, then Hamilton-style corrects the rounding drift so the sum is exact.
  Seeded by a string (`"{audience}-device"` etc.) → **deterministic per campaign/section**. [CONFIRMED]
- **VCR handling** — uses the DATE-sheet Grand-Total VCR directly (openpyxl can't read the
  template's Excel formula, so it's recomputed as ΣCV/ΣStarts). `None` → "-".

## Number formats [CONFIRMED]

`d"-"mmm` (dates), `#,##0` (counts), `0.00%` (CTR/VCR), `0%` (pacing),
`$#,##0.00;[Red]\-"$"#,##0.00` (currency). Blue fill `0000FF` white bold; yellow `FFFF00`.

## Database interactions

`ctr_db.reach_report_store` (raw SQL; table auto-created by `_ensure_table()`):
columns `report_filename, campaign_label, platform, format_type, file_data (bytea)`,
plus id/created timestamp. Used for history list/download/delete.

## Edge cases & known limitations

- Booked Impressions is always looked up as `booked_impressions[f"{audience}_{burst}"]`
  but the template parser never populates that dict → **Booked Impressions is effectively
  0** and Campaign/Impression Pacing formulas divide against it. [CONFIRMED — limitation]
- All 10 sheets must be present in every input or parsing raises `ValueError`.
- Reach/Complete-View allocation is proportional to impressions only (no true per-row data).
- Investment column is left blank for manual entry; Amount Spent formula depends on it.
- Audience detection can misfire on unusual filenames (falls back to "General").
