# Data Dictionary

Covers the important fields across databases, request payloads, internal objects,
and Excel columns. "Transformation" describes how the value is derived.

---

## `ctr_db` tables

### `campaign_rules` (ORM: `models/crm.py :: CampaignRule`)

| Field | Type | Source | Used By | Description |
|-------|------|--------|---------|-------------|
| id | int PK | auto | CRM | Row id |
| line_item_id | str | user | CRM rule lookup | Matched against normalized Line Item ID |
| campaign_name | str? | user | CRM rule lookup | Alternate match key |
| min_ctr / max_ctr | float? | user | `process_rows` | CTR band (percent, e.g. 0.40) |
| min_vcr / max_vcr | float? | user | `process_rows` | VCR band (percent, e.g. 80) |
| min_viewability / max_viewability | float? | user | `process_rows` | Viewability band (percent) |
| enabled | bool | user | `_load_db_rules` (filters enabled) | Toggle |
| created_at / updated_at | datetime | auto | — | Audit |

### `global_settings` (`GlobalSetting`)

| Field | Type | Used By | Description |
|-------|------|---------|-------------|
| id | int PK | — | Single settings row |
| min_ctr / max_ctr | float? | `_load_global_settings` | Global CTR fallback band. VCR/viewability NOT stored here (come from request). |

### `processed_files` (`ProcessedFile`)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| id | int PK | auto | — |
| original_filename | str | upload | Original name |
| saved_filename | str | CRM | `processed_{stem}[...].csv` on disk |
| processed_at | datetime | run | Timestamp |
| ad_type | str | `_detect_ad_type` | "Video" or "Banner" |

### `yesterday_memory` (`YesterdayMemory`)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| id | int PK | auto | — |
| line_item_id | str | run | Normalized LID key |
| clicks | int | run | Yesterday's generated clicks |
| ctr | str | run | Yesterday's CTR string ("0.42%") |
| run_date | str | run | DD/MM/YYYY of the run |

> **Lifecycle:** wiped and replaced every `/crm/process` run — only the most recent run
> is remembered.

### `users` (`models/user.py :: User`)

| Field | Type | Description |
|-------|------|-------------|
| id | int PK | — |
| username | str unique | Login id |
| email | str? unique | — |
| hashed_password | str | bcrypt hash |
| role | str | "admin" \| "super_admin" |
| allowed_pages | JSON? | None = all pages; else list of page keys |
| is_active | bool | Deactivation flag |
| created_at / last_login | datetime | — |

### `scan_screenshots` (`models/scan_screenshot.py :: ScanScreenshot`)

Key fields: `scan_job_id`, `url`, `domain`, `device`, `status`, `ads_found`,
`slots_injected`, `creative_name`, `creative_size`, `injection_type`, `match_score`,
`notes`, `screenshot_data` (BYTEA), `original_data` (BYTEA), `mime_type`,
`file_size_kb`, `captured_at`.

### `final_report_store` (raw SQL, `routers/final_report.py`)

`id, campaign_name, report_filename, generated_at, file_data (BYTEA),
qc_status, qc_impressions, qc_clicks, qc_ctr, qc_submitted_at, qc_results (TEXT/JSON)`.

### `reach_report_store` (raw SQL, `routers/reach_report.py`)

`id, report_filename, campaign_label, platform, format_type, file_data (BYTEA)`, timestamp.

### `app_url_reference` (raw SQL, root script `rebuild_app_url_reference.py`)

| Field | Type | Description |
|-------|------|-------------|
| sheet_name | varchar | Language/segment grouping key |
| url_id | int | Source id |
| url | varchar | The site URL |
| priority | varchar(20) | `user_site` \| `more_important` \| `important` \| `regular` |

Consumed by `report_generator.get_urls_from_sheets()` (tier-ordered, shuffled within tier).

### `city_reference` (raw SQL, root script `migrate_city_db.py`)

| Field | Type | Description |
|-------|------|-------------|
| sheet_name | varchar | Grouping key |
| city_name | varchar | City |
| potential_impressions | bigint | Weight (primary) |
| unique_cookies | bigint | Weight (fallback) |

Consumed by `report_generator.load_city_db_sheet()` → `{name, weight}` (weight =
`COALESCE(potential_impressions, unique_cookies, 1)`).

---

## `scanner_db.screenshot_results` (`models/screenshot.py`)

`id, url, screenshot_path, original_screenshot_path, status, ads_found, matches_found,
created_at, matched_creative_name, matched_creative_size, injection_type, device`.

---

## CRM request payload (`schemas/crm.py`)

| Field | Type | Default | Note |
|-------|------|---------|------|
| CampaignRule.campaign | str | — | comma-separated names allowed |
| CampaignRule.line_id | str? | None | — |
| CampaignRule.ctr_min/ctr_max | float? | None | percent |
| CampaignRule.vcr_min/vcr_max | float? | None | percent |
| CampaignRule.view_min/view_max | float? | None | percent |
| GlobalSettings.ctr_min | float | 0.10 | percent |
| GlobalSettings.ctr_max | float | 0.55 | percent |
| GlobalSettings.vcr_min/vcr_max | float | 75.0 / 89.0 | percent |
| GlobalSettings.view_min/view_max | float | 75.0 / 89.0 | percent |

> **Field-name renaming to watch:** the API/schema uses `ctr_min/ctr_max/vcr_min/...`
> and `line_id`, but the **DB model + `process_rows` rule dict** use
> `min_ctr/max_ctr/min_vcr/...` and `line_item_id`. `routers/crm.py` maps between them
> (`_merge_form_rules`, `create_campaign_rule`). Do not confuse the two naming schemes.

---

## CRM Excel — input vs output columns

**Input columns read by `process_rows`:** `Impressions`, `Line Item ID`, `Line Item`,
`Campaign`, `Campaign ID`, `Date`, `Start Views`, `Complete Views`,
`Measurable Impressions`, `Viewable Impressions`.

**Output columns (`OUTPUT_COLUMNS`, exact order):** Advertiser, Advertiser ID,
Advertiser Currency, Insertion Order, Insertion Order ID, Line Item, Line Item ID, Date,
Campaign, Campaign ID, Impressions, Billable Impressions, Clicks, Click Rate (CTR),
Revenue (Adv Currency), Media Cost (Advertiser Currency), Start Views, 1st Quartile Views,
Midpoint Views, 3rd Quartile Views, Complete Views, Video Completion Rate,
Viewable Impressions, Measurable Impressions, Viewability,
For Checking (Measurable-Impression), Start Views-Impression.

| Output field | Transformation |
|--------------|----------------|
| Clicks | Generated in `[ceil(min%·imp), floor(max%·imp)]`, de-duplicated vs group + yesterday |
| Click Rate (CTR) | `Clicks/Impressions` as `"x.xx%"` |
| Start Views / Complete Views | Regenerated to hit VCR band; gap-enforced vs Impressions |
| Video Completion Rate | `Complete/Start` as `"x.xx%"` (0 if no starts) |
| Measurable / Viewable Impressions | Regenerated to hit viewability band; gap-enforced |
| Viewability | `Viewable/Measurable` as `"x.xx%"` |
| For Checking (Measurable-Impression) | `Measurable − Impressions` (0 if measurable 0) |
| Start Views-Impression | `Start − Impressions` (0 unless original SV & imp nonzero) |

---

## Final Report — internal per-sheet objects

Each `build_sheetN_*()` returns `(rows: list[dict], total_row: dict)`. Common keys per
row: `Impressions`, `Clicks`, `Click Rate (CTR)`, plus a dimension label
(`Date`, `City`, `Device`, `Age`, `Gender`, `App URL`, `Exchange`, `Hour`, `Creative`).
Video sheets add `Sum of Starts (Video)`, `Sum of Complete Views (Video)`,
`VCR (Completion Rate)`, `Viewable/Measurable Impressions`.

---

## Reach Report — dataclasses (`reach_parser.py`)

- `ReachData(actual_impressions, link_clicks, ctr, reach, frequency, complete_views, vcr)`
- `DeviceBreakdown / CreativeBreakdown / AgeBreakdown / GenderBreakdown(name/label, impressions, clicks, ctr)`
- `CampaignData(audience, burst_number, reach_data, *_breakdown[], start_date, end_date)`
- `TemplateMetadata(platform, format_type, booked_impressions{}, start_date{}, end_date{}, reporting_date{}, audience_labels{})`
