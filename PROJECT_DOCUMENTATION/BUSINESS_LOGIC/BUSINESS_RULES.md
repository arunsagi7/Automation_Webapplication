# Business Rules & Hardcoded Logic

Format: **Rule → Where implemented → What happens if changed.** "Why" is given where
inferable. These are the hidden/hardcoded rules a future editor must not break unknowingly.

---

## CRM Excel Generator (`services/crm_processor.py`)

1. **Default CTR band = 0.10%–0.55%.**
   `schemas/crm.py :: GlobalSettings.ctr_min=0.10, ctr_max=0.55`; function-signature
   default in `process_rows` is 0.37/0.55.
   → Change: shifts all generated click volumes. DB `global_settings` row overrides ctr min/max.

2. **Default VCR & Viewability band = 75%–89%.**
   `_metric_bounds(default_min=75.0, default_max=89.0)` and `schemas` defaults.
   → Change: regenerated Start/Complete Views and Viewable/Measurable to fit new band.

3. **Impression-gap bands (Measurable/Start Views vs Impressions):**
   `get_gap_range`: `<500 → (1,20)`, `≤3000 → (50,100)`, `>3000 → (100,200)`.
   Why: keep Measurable/Start Views realistically just below Impressions.
   → Change: alters the "For Checking" and "Start Views-Impression" deltas.

4. **De-dup retry budget = 150 attempts** (both Step 1 CTR pick and Step 2 group de-dup).
   → Change: raising improves uniqueness on tight ranges at CPU cost; lowering risks dupes.

5. **Sequential gap between consecutive clicks in a Line Item group:**
   `_seq_gap = 2 if (max-min) >= 4 else 1`.
   → Change: affects how "spread out" clicks look within a line item.

6. **Rule lookup priority:** Line Item ID → Line Item name → `li_id|li_name` → Campaign
   name → Campaign ID (`_find_rule`). First match wins.
   → Change: changes which override applies when multiple could match.

7. **Line Item ID normalization:** strip, split on `|`, drop trailing `.0`, lowercase
   (`_normalize_lid`).
   → Change: could break matching against DB rules and yesterday_memory keys.

8. **`yesterday_memory` is fully replaced each run** (`save_today_snapshot` deletes all
   rows then inserts today's). Only the last run is remembered.
   Why: de-dup is day-over-day, not full history.
   → Change: to remember multiple days you must change the delete-then-insert logic.

9. **Ad-type detection keywords:** `{video, vid, 15s, 30s, 6s, bumper, outstream, instream}`
   (`_VIDEO_KEYWORDS`). Name contains one → "Video", else "Banner".
   → Change: mis-tags processed_files ad_type.

10. **Impressions ≤ 0 → Clicks=0, CTR="0.00%"**, VCR/viewability skipped.

11. **Zero Start Views → VCR "0.00%"; no VCR data → renders as literal in output.**

---

## Reach Report Generator (`services/reach_generator.py`, `reach_parser.py`)

12. **Required sheets (all 10 must exist)** or parsing raises ValueError (`REQUIRED_SHEETS`).
    → Change: relaxing lets partial files through but downstream parsers assume the sheets.

13. **Frequency default = 3** (`_parse_reach_sheet` `or 3.0`; `FREQUENCY = 3` constant in breakdown rows).
    → Change: alters reach/impression relationship in the workbook.

14. **Canonical campaign order** `_EXPECTED_ORDER` (Vietnamese/Punjabi bursts 1–3, then
    Arabic, Chinese, Korean, Hindi). Unlisted → appended.
    → Change: reorders Overview and Performance sections.

15. **Reach/Complete-View allocation is impression-proportional with seeded noise**
    (`_allocate_reach`, seed `"{audience}-{dimension}"`), Hamilton-corrected to exact sum.
    Deterministic per campaign/section.
    → Change: changes per-row reach distribution.

16. **VCR recomputed as ΣComplete/ΣStarts** from the DATE sheet (template formulas
    unreadable by openpyxl). No VCR column → "-".

17. **Audience keyword list `_AUDIENCE_KEYWORDS`** (~50 languages) drives filename parsing;
    fallbacks to word-before-"burst" or "General".

18. **Number formats & colors are fixed** (blue `0000FF`, yellow `FFFF00`, `0.00%`, `#,##0`,
    `d"-"mmm`, currency mask) to match the client template.

---

## Final Report Generator (`services/report_generator.py`, `routers/final_report.py`)

19. **Fabricate totals when input has none:** `total_imp = randint(150_000, 300_000)`;
    `total_clk = round(total_imp * rand(0.0040, 0.0055))` (0.40%–0.55% CTR).
    → Change: baseline scale/CTR of synthesized reports.

20. **Per-row CTR hard ceiling = 0.90%** (`_SANITIZE_MAX_CTR = 0.009`), excess redistributed.
    Also enforced in `build_sheet10_apps`.
    → Change: relaxing produces higher (less realistic) per-row CTRs.

21. **Synthetic date range = 30 days** when no Date column, distributed via `_largest_remainder`.

22. **App URL priority tiers:** `user_site > more_important > important > regular`
    (`get_urls_from_sheets`), shuffled within each tier.
    Source boxes in `rebuild_app_url_reference.py`: A-B=regular, E-F=important, I-J=more_important.
    → Change: reorders which sites appear first in the APP URL sheet.

23. **City weighting:** `weight = COALESCE(potential_impressions, unique_cookies, 1)`
    (`load_city_db_sheet`), impressions distributed proportionally.

24. **Grand-Total rows are literal reference values**, never `=SUM()` (so QC/openpyxl can
    read them). Enforced by `_sanitize_sheet_data` Step 4 + `_pre_write_qc_fix`.
    → Change: breaking this makes QC unable to verify totals.

25. **`mode` (video/banner) is user-supplied and never auto-overridden**, even if a
    banner-format file is detected. Box-format files can be either type.

26. **Block-name detection:** Format A (Line Item column value) preferred over Format B
    (box B1 label); sheet-tab names truncated to 31 chars and de-duplicated.

27. **Video-column detection set** `_VIDEO_COLS` (standard + legacy variant header names)
    used to classify Video vs Banner from headers when name keywords are absent.

28. **QC status mapping:** no fail/warn → `approved`; warn → `warning`; fail with no
    corrections → `rejected`; fail but auto-corrected → `warning`.

---

## Auth (`core/security.py`, `main.py`)

29. **JWT:** HS256, secret from `JWT_SECRET` (default placeholder if unset — logs a warning
    in production), expiry `ACCESS_TOKEN_EXPIRE_MINUTES` default **480 (8h)**.

30. **Default super_admin auto-created** if `users` empty: `admin` / `admin123`.
    → ⚠️ Security: change/remove for production (see KNOWN_ISSUES).

31. **Role/page model:** `super_admin` → `allowed_pages=None` (all). `admin` → explicit
    page-key list. Page keys: `scanner, crm_excel, ppt_store, final_report`.

---

## Scanner (`services/browser.py`, `smart_placement.py`, config)

32. **Concurrency = `ENGINE_CONCURRENCY`** (default 8 in config, 5 in `.env.example`).
    Guidance in comments: 3 on 512MB, 8 on 2GB, 20 on 4GB.

33. **Navigation timeout = `ENGINE_NAV_TIMEOUT_MS`** (default 45000).

34. **Post-injection wait = 1500ms** (`POST_MASK_WAIT_MS`) before screenshot.

35. **Slot-detection fallback order:** DOM (`ad_detector`) → Claude Vision (if
    `ANTHROPIC_API_KEY`) → smart placement (structural DOM → vision → native article).
    Vision cost noted ~\$0.001/call (Haiku).

36. **Creative → site mapping** from `site_creatives.json`; creatives injected at
    **original dimensions** (never scaled/compressed — comment in `browser.py`).

37. **IST timezone (UTC+5:30)** used for timestamp display in `db_service.py`.
