# Scanner / Screenshot Engine — Full Audit Report
**AdVision AI / Creative Scanner Pro**
Audited: 2026-06-17

---

## Files Covered

| File | Lines | Role |
|------|-------|------|
| `services/browser.py` | 2406 | Core orchestrator, injection, screenshots |
| `services/ad_detector.py` | 958 | DOM scan, confidence scoring, mutation observer |
| `services/image_utils.py` | 481 | Creative loading, scoring, auto-resize |
| `services/vision_detector.py` | 161 | Claude AI fallback ad detection |
| `services/db_service.py` | 127 | scanner_db CRUD |
| `services/screenshot_storage.py` | 227 | ctr_db binary screenshot storage |

---

## How the Pipeline Works (Summary)

1. `open_website()` launches a persistent Chromium context (cookies accumulate across runs — looks like a returning user to bot detectors)
2. Auto-detects device: if every uploaded creative is ≤ 414px wide, auto-switches to mobile viewport (390×844, iPhone 14 Safari UA)
3. For each URL, `process_single_url()` runs:
   - Stealth init script + playwright-stealth to mask automation signals
   - CSP header stripping + resource blocking (fonts, media, analytics, ad networks in Pass 2 only)
   - Navigate with 3-attempt retry + exponential backoff + `commit` fallback
   - Security page check (Cloudflare, reCAPTCHA, hCaptcha) → early exit if blocked
   - Accept GDPR/cookie consent banners → wait 1.5s for consent JS to propagate
   - Wait up to 8s for GPT/DFP iframes to render
   - Quick above-fold DOM scan → full scroll-and-collect if nothing found
   - **Original screenshot** taken with real ads visible
   - **Claude Vision** (if `ANTHROPIC_API_KEY` set) merges AI-detected slots with DOM slots
   - Filter pipeline: zero-size → off-screen → non-ad keywords → IAB device filter → confidence ≥ 65
   - Sort slots: adchoices-confirmed > gpt-api > generic, then by confidence tier, shape match, above-fold position
   - Inject creative into **single best slot** via body-level `position:absolute` overlay (`data-injected="1"`)
   - Verify overlay exists → re-inject once if page script cleared it
   - Scroll to slot, inject fake address bar overlay (desktop or mobile), take focused screenshot
   - Build before/after comparison composite image
   - Save to both `scanner_db` (path-based) and `ctr_db` (binary BYTEA)

---

## Bugs Found

### 🔴 CRITICAL — Already Fixed

**`ad_detector.py` line 640: corrupted text inside JavaScript string**

A Windows command `taskkill /PID <PID> /F` was pasted into the middle of the `DOM_SCAN_SCRIPT` JavaScript source string:

```js
// BEFORE (broken):
const cls = typeof el.className === 'string'
taskkill /PID <PID> /F                    ? '.' + el.className...

// AFTER (fixed):
const cls = typeof el.className === 'string'
                    ? '.' + el.className.trim().split(/\s+/)[0] : '';
```

**Impact:** The entire Sidebar IAB Positional Scan section of `DOM_SCAN_SCRIPT` would throw a `SyntaxError` at evaluation time. Because this section is inside a `try/catch` in the JS, the script wouldn't crash, but all sidebar-iab-size positional slots (right-rail 300×250, 300×600, 160×600, etc.) would silently never be detected. This is fixed.

---

### 🟠 HIGH — Should Fix

**1. `engine_concurrency` mismatch between `config.py` and `browser.py`**

`config.py` defines `engine_concurrency: int = 30` but `browser.py` reads the env var directly:
```python
DEFAULT_MAX_CONCURRENCY = max(1, int(os.getenv("ENGINE_CONCURRENCY", "50")))
```
The `config.py` value is never used by the browser engine. The effective default is **50**, not 30.
- **Fix:** Change line ~50 in browser.py to `from core.config import get_settings as _cfg_early` and use `_cfg_early().engine_concurrency`, OR just update the hardcoded default from 50 to 30 to match intent.

**2. `screenshots/` folder uses a relative path**

```python
os.makedirs("screenshots", exist_ok=True)
screenshot_path = f"screenshots/{domain}.png"
```
This resolves relative to the process working directory. If uvicorn is launched from a different directory than `Backend_Screenshot/`, screenshots go to the wrong folder or fail silently.
- **Fix:** Use `core/paths.py` (which already exists and returns absolute paths):
  ```python
  from core.paths import get_paths
  paths = get_paths()
  screenshot_path = os.path.join(paths["screenshots"], f"{domain}.png")
  ```

**3. Dead imports in `browser.py`**

Two services are imported but never called:
```python
from services.ppt_style_extractor import get_ppt_styles       # never called
from services.smart_placement import find_smart_placement      # never called
```
These add startup overhead and are confusing. Remove both import lines.

---

### 🟡 MEDIUM — Worth Fixing

**4. Stale comment contradicts actual code (single-slot injection)**

Line 1937 comment says:
> "We no longer stop after the first success — we fill every valid slot."

But `MAX_INJECT_SLOTS = 1` on line 1879 means the candidate loop exits after building exactly 1 candidate. Only one slot is ever injected per page, regardless of how many valid slots were found.

Either remove the stale comment or increase `MAX_INJECT_SLOTS` to the intended number. The mismatch between the comment and code is a future maintenance trap.

**5. `get_local_creatives()` re-reads files on every URL**

`get_local_creatives()` opens and base64-encodes every image file from disk on each call. With 50 concurrent URLs, this means the same creative files are read 50 times simultaneously. The `_SITE_CREATIVES_CONFIG` (the JSON mapping) is cached, but the actual image data is not.

- **Fix:** Cache the result of `get_local_creatives()` with a module-level dict keyed by `(directory, device)`. Invalidate on file modification time or on server restart. This is safe because creatives are uploaded via API and the cache can be cleared on upload.

**6. Stale `_PASS1_PLACEMENT_JS_OLD` dead code (200+ lines)**

The old DOM-replacement injection approach is kept "for reference" but is never used. The new body-overlay approach (`_PASS1_PLACEMENT_JS`) replaced it. Having 200 lines of commented-but-not-commented code in the middle of the file is confusing.

- **Fix:** Delete `_PASS1_PLACEMENT_JS_OLD` entirely. Git history preserves it if ever needed.

**7. Vision detection runs after original screenshot**

`detect_ads_with_vision()` is called after the original screenshot is taken. So if Claude Vision finds a slot the DOM scan missed, the "before" screenshot won't show the real ad in that slot — only the "after" screenshot will show the injected creative there. This is an architectural limitation but worth documenting.

**8. `_save_to_db()` swallows ctr_db write failures silently**

```python
try:
    await asyncio.to_thread(_save_to_ctr_db, ...)
except Exception as _ctr_err:
    logger.warning("[CTR-DB] Failed to save screenshot for %s: %s", url, _ctr_err)
```
The warning is logged but the scan result is still returned as "success". If ctr_db is down, the frontend shows success but the binary screenshot is never saved. This is acceptable for resilience but the UI has no way to know — consider adding a `ctr_db_saved: bool` field to the result dict so the frontend can warn.

---

### 🔵 LOW / INFO

**9. `filter_non_ad` log line counts wrong**

```python
good_slots = filtered_non_ad
logger.info("[INJECT] Blocked %d non-ad element(s)",
            len(good_slots) - len(filtered_non_ad))
# ↑ Both are the same list at this point — always logs 0
```
The subtraction should happen before the reassignment. Fix:
```python
blocked_count = len(good_slots) - len(filtered_non_ad)
good_slots = filtered_non_ad
logger.info("[INJECT] Blocked %d non-ad element(s)", blocked_count)
```

**10. `CORS allow_origins=["*"]` in `main.py`**

Production should restrict this to the specific frontend domain. There's already a comment noting this — just needs to be done before going live.

**11. `JWT_SECRET` in `.env` is weak**

Current value: `creativescannerpro-jwt-secret-change-in-production`. Change to a cryptographically random 256-bit secret before production deployment. (`python -c "import secrets; print(secrets.token_hex(32))"`)

**12. `/final-report/` and `/crm/` routers have zero authentication**

All endpoints in `final_report.py` and `crm.py` are fully public — no `Depends(require_api_key)`. Any unauthenticated user can access uploaded reports and CRM data. This was flagged in the earlier audit. These routers need auth guards added to every endpoint.

---

## What's Working Well

- **Injection approach is solid.** Body-level `position:absolute` overlay with `data-injected="1"` is GPT-proof — ad networks cannot touch body-level elements, so the creative survives GPT refresh cycles. The old DOM-replacement approach (kept as `_OLD`) was vulnerable to this.
- **AdChoices detection is excellent.** Three-pass approach (ins[data-ad-status="filled"] → aswift_ iframes → *_host divs) reliably finds confirmed rendered Google ads with high confidence (95%). This is the highest-quality signal available.
- **GPT API slot scan** queries `googletag.pubads().getSlots()` directly for pre-configured sizes — catches zero-dimension slots that DOM scanning would miss.
- **Auto-resize fallback** (`resize_creative_for_slot`) with contain-fit means a creative is always fully visible even when no exact size match exists.
- **Vision detection integration** is well-engineered — Claude Haiku is fast and cheap (~$0.001/image), runs async, merges with DOM slots without duplicates, and fails gracefully when the API key is missing.
- **Before/after composite** image is a great client-facing feature — shows the real ad replaced by the client creative side-by-side.
- **Persistent browser context** with separate `browser_data_desktop/` and `browser_data_mobile/` user data directories is smart — builds up cookies/history to look like a real returning user.
- **`db_service.py`** is clean: session management, IST timezone conversion, proper rollback on failure.
- **`screenshot_storage.py`** correctly reads files from disk and stores binary BYTEA — no dangling file references in ctr_db.

---

## Summary Table

| # | Severity | File | Issue | Status |
|---|----------|------|-------|--------|
| 1 | 🔴 Critical | `ad_detector.py:640` | `taskkill` text corrupted JS → sidebar scan broken | **FIXED** |
| 2 | 🟠 High | `browser.py:~50` | Concurrency default 50 vs config.py 30 — mismatch | Open |
| 3 | 🟠 High | `browser.py:1574` | `screenshots/` relative path — wrong dir on startup | Open |
| 4 | 🟠 High | `browser.py:17-19` | Dead imports (`ppt_style_extractor`, `smart_placement`) | Open |
| 5 | 🟡 Medium | `browser.py:1937` | Stale "fill every slot" comment vs `MAX_INJECT_SLOTS=1` | Open |
| 6 | 🟡 Medium | `image_utils.py` | `get_local_creatives()` not cached — re-reads disk per URL | Open |
| 7 | 🟡 Medium | `browser.py:1236` | `_PASS1_PLACEMENT_JS_OLD` dead code (200+ lines) | Open |
| 8 | 🟡 Medium | `browser.py:1824` | `filter_non_ad` log line always prints 0 | Open |
| 9 | 🔵 Low | `main.py:53` | CORS `allow_origins=["*"]` — lock down for production | Open |
| 10 | 🔵 Low | `.env` | Weak `JWT_SECRET` value | Open |
| 11 | 🔴 High | `final_report.py`, `crm.py` | Zero authentication on all endpoints | Open |
