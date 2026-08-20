# MODULE — CRM Excel Generator

## Purpose

Takes an uploaded campaign performance file (DV360 / "CRM uploading" style export)
and **generates realistic, internally-consistent metrics** for each row:
- `Clicks` and `Click Rate (CTR)` within configured min/max CTR ranges,
- `Video Completion Rate` (VCR) via Start/Complete Views,
- `Viewability` via Viewable/Measurable Impressions,

while ensuring generated numbers are **not duplicated within a line item** and **not
identical to yesterday's run** (persisted in `yesterday_memory`). It also enforces
"gap" rules between Measurable/Start Views and Impressions.

It is a Python port of an original **n8n JavaScript workflow** (stated in the
`crm_processor.py` docstring).

## Files involved

| File | Role |
|------|------|
| `routers/crm.py` | HTTP endpoint(s), DB I/O, file read/write, rule merging, orchestration |
| `services/crm_processor.py` | **Core row-level generation logic** (`process_rows`) — no I/O |
| `services/crm_excel_writer.py` | `build_excel()` — styled `.xlsx` writer (available; `/process` uses CSV) |
| `services/crm_memory.py` | Load/save `yesterday_memory` in `ctr_db` |
| `models/crm.py` | ORM models: `CampaignRule`, `GlobalSetting`, `ProcessedFile`, `YesterdayMemory` |
| `schemas/crm.py` | Pydantic `CampaignRule`, `GlobalSettings` request schemas |

## Endpoints (`routers/crm.py`, prefix `/crm`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/crm/process` | Main pipeline. Form: `file`, `rules` (JSON array), `settings` (JSON object). Returns `.csv` or `.zip`. |
| GET | `/crm/rules` | List all `campaign_rules`. |
| POST | `/crm/rules` | Create a rule. |
| PUT | `/crm/rules/{rule_id}` | Update a rule. |
| DELETE | `/crm/rules/{rule_id}` | Delete a rule. |
| GET | `/crm/processed-files` | List processed-file audit log (newest first). |
| GET | `/crm/download/{filename}` | Re-download a previously processed file from disk. |

## Inputs

**Uploaded file:** `.xlsx`, `.xls`, or `.csv`. Read by `_read_file()`:
- CSV → single "sheet" keyed by filename stem.
- Excel → **all sheets** read (`pd.read_excel(sheet_name=None)`), empty sheets skipped.
- Read as strings/objects with blanks → `None` (`keep_default_na=False`).

**Expected input columns** (the generator reads these; others pass through):
`Impressions`, `Line Item ID`, `Line Item`, `Campaign`, `Campaign ID`, `Date`,
`Start Views`, `Complete Views`, `Measurable Impressions`, `Viewable Impressions`.
Rows are keyed to rules via Line Item ID / name / Campaign name / Campaign ID.

**Rules (`rules` form field, JSON array of `schemas.crm.CampaignRule`):**
`campaign` (comma-separated names), `line_id`, `ctr_min`, `ctr_max`, `vcr_min`,
`vcr_max`, `view_min`, `view_max`. These **override** DB rules for matching keys.

**Settings (`settings` form field, JSON `schemas.crm.GlobalSettings`):**
`ctr_min` (default 0.10), `ctr_max` (0.55), `vcr_min` (75.0), `vcr_max` (89.0),
`view_min` (75.0), `view_max` (89.0). CTR min/max may be overridden by the
`global_settings` DB row.

## Output

**Output columns (fixed order, `OUTPUT_COLUMNS` in `crm_processor.py`):**
`Advertiser`, `Advertiser ID`, `Advertiser Currency`, `Insertion Order`,
`Insertion Order ID`, `Line Item`, `Line Item ID`, `Date`, `Campaign`, `Campaign ID`,
`Impressions`, `Billable Impressions`, `Clicks`, `Click Rate (CTR)`,
`Revenue (Adv Currency)`, `Media Cost (Advertiser Currency)`, `Start Views`,
`1st Quartile Views`, `Midpoint Views`, `3rd Quartile Views`, `Complete Views`,
`Video Completion Rate`, `Viewable Impressions`, `Measurable Impressions`,
`Viewability`, `For Checking (Measurable-Impression)`, `Start Views-Impression`.

**File output:** single input sheet → `processed_{stem}.csv`; multiple sheets →
`processed_{stem}_{sheet}.csv` each, zipped as `processed_{stem}.zip`.

## Execution flow (step-by-step)

```
Upload
 → validate ext (xlsx/xls/csv)
 → parse rules + settings (422 on bad JSON)
 → load db rules + global settings + yesterday_memory (ctr_db)
 → merge form rules over db rules
 → _read_file → {sheet: rows}
 → for each sheet: process_rows(...)
      Step 0  Date normalization
      Step 1  CTR/Clicks generation (respect ranges + yesterday memory)
      Step 2  In-group de-duplication
      Step 3  VCR + Viewability generation (+ gap enforcement)
      Step 4  Build OUTPUT_COLUMNS rows
 → merge today_snapshot across sheets
 → CSV per sheet → save to disk → log processed_files
 → save_today_snapshot (REPLACE yesterday_memory)
 → return csv or zip
```

## `process_rows()` — the core function (plain-English)

Signature:
```python
process_rows(rows, yesterday_memory, global_min_ctr=0.37, global_max_ctr=0.55,
             campaign_ctr_rules=None) -> (output_rows, today_snapshot)
```
> Note: the router passes `global_settings.ctr_min/ctr_max` (defaults 0.10/0.55 from
> the Pydantic schema, or the DB `global_settings` row), so the function-signature
> defaults of 0.37/0.55 are only used if called directly. [CONFIRMED]

**Step 0 — Date normalization.** Each `Date` is converted to `DD/MM/YYYY`.
Handles Excel date serials (`excel_serial_to_date_string`, epoch offset 25569) and
string variants (`normalize_date_string`).

**Step 1 — CTR / Clicks generation.** For each row:
- Look up a rule via `_find_rule()` (priority: exact Line Item ID → Line Item name →
  `li_id|li_name` → Campaign name → Campaign ID).
- `min_pct/max_pct` = rule CTR bounds or the globals.
- If `Impressions <= 0`: Clicks=0, CTR="0.00%".
- Else compute `min_clicks = ceil(min_pct% * impressions)`, `max_clicks = floor(max_pct% * impressions)`.
- If range inverted, pick the midpoint.
- Otherwise pick a random integer in `[min_clicks, max_clicks]`, retrying up to **150 times**
  to avoid any clicks/CTR already present in `yesterday_memory[line_id]`.
- Store `_min`/`_max` on the row for Step 2.

**Step 2 — In-group de-duplication.** Rows grouped by normalized Line Item ID, sorted
by impressions. Within a group, tracks used clicks/CTRs (seeded with yesterday's) and
enforces a **sequential gap** (≥2 apart when range width ≥4, else ≥1). Re-rolls up to
150 times; final fallback relaxes the sequential constraint.

**Step 3 — Video (VCR) + Viewability.**
- Saves `_originalSV` (original Start Views).
- **VCR:** if `Start Views == 0` → VCR "0.00%". Else `enforce_gap()` on Start Views vs
  Impressions, compute `vcr = complete/starts`; if outside `[vcr_min, vcr_max]` (rule or
  default 75–89%), regenerate Start Views (within impression gap) + Complete Views to hit
  the target band.
- **Viewability:** `enforce_gap()` on Measurable; `viewability = viewable/measurable`; if
  out of band, regenerate both to hit `[view_min, view_max]`.

**Step 4 — Output projection.**
- `For Checking (Measurable-Impression)` = `measurable - impressions` (0 if measurable 0).
- `Start Views-Impression` = `start - impressions` (0 unless both original SV and impressions nonzero).
- Project each row to `OUTPUT_COLUMNS`; trim strings; `None` for blanks.

**Returns** `today_snapshot`: `{line_item_id: [{"clicks", "ctr"}, ...]}` — the caller
persists it to `yesterday_memory` so **tomorrow's run avoids today's numbers**.

## Key helper functions

| Function | Purpose |
|----------|---------|
| `safe_int(val)` | Robust int coercion (handles nan/NaT/"" → 0). |
| `get_gap_range(impressions)` | Gap band: `<500 → (1,20)`, `≤3000 → (50,100)`, else `(100,200)`. |
| `enforce_gap(value, impressions)` | Force `value` into `[imp-max_gap, imp-min_gap]`; 0 stays 0. |
| `_normalize_lid(val)` | Normalize Line Item ID (strip, drop `.0`, split on `|`, lower). |
| `_find_rule(row, rules)` | Rule lookup by the 5-key priority chain. |
| `_metric_bounds(rule, min_key, max_key)` | Return `(lo/100, hi/100)` fractions, default 75–89. |

## Router helpers (`routers/crm.py`)

| Function | Purpose |
|----------|---------|
| `_load_db_rules(db)` | `campaign_rules` (enabled) → lookup dict keyed by lower(line_item_id) and lower(campaign_name). |
| `_load_global_settings(db, fallback)` | Read `global_settings` row; only CTR min/max stored there — VCR/viewability come from request. |
| `_merge_form_rules(base, form_rules)` | Form rules override DB rules per key (splits `campaign` on commas). |
| `_detect_ad_type(sheet_name)` | "Video" if name has a video keyword, else "Banner". Keywords: `video, vid, 15s, 30s, 6s, bumper, outstream, instream`. |
| `_read_file(data, filename)` | Read all sheets/CSV → `{sheet: [rows]}`. |

## Excel writer (`crm_excel_writer.py :: build_excel`)

Builds a styled `.xlsx` with a single sheet `"Processed"`. Column typing:
- `PERCENT_COLS` (CTR, VCR, Viewability) → value/100 with `"0.00%"` format.
- `INTEGER_COLS` → int. `FLOAT_COLS` (Revenue, Media Cost) → float. Else string.
- Suppresses "number stored as text" warnings via `ignored_errors`.
> **`build_excel` is not called by `/crm/process`** (which emits CSV). It's available
> for `.xlsx` output but currently unused by that route. [CONFIRMED]

## Database interactions (all `ctr_db`)

- Reads `campaign_rules`, `global_settings`, `yesterday_memory`.
- Writes `processed_files` (audit log; unique `saved_filename` → IntegrityError→update path).
- Replaces `yesterday_memory` wholesale each run (`save_today_snapshot` deletes all then inserts).

## Business rules embedded here

See `BUSINESS_LOGIC/BUSINESS_RULES.md` for the full list. Highlights:
- Default CTR band 0.10–0.55%; default VCR/viewability band 75–89%.
- Retry budget = 150 attempts for de-dup rolls.
- Impression-gap bands are hardcoded thresholds (500 / 3000).
- `yesterday_memory` is replaced (not appended) — only the **last** run is remembered.

## Edge cases & known limitations

- `Impressions <= 0` → zeros for clicks/CTR; VCR/viewability skip.
- If the configured CTR range yields `max_clicks < min_clicks`, a midpoint is forced.
- If a Line Item's full click range is exhausted by yesterday's memory, it falls back to
  the first non-duplicate click, or a random pick — duplicates become **possible** in
  pathological cases. [CONFIRMED]
- Randomness is **not seeded** in `crm_processor` (uses global `random`), so output is
  non-deterministic per run. [CONFIRMED]
- Multi-sheet uploads share one `yesterday_memory` and merge snapshots — cross-sheet
  line items with the same ID interact. [INFERRED]
- Endpoint emits CSV, so `.xlsx` number formatting from `build_excel` is not applied on the
  primary path. [CONFIRMED]
