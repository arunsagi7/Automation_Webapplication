# Creative Scanner Pro

**Creative Scanner Pro** is an ad verification and simulation platform. It opens any website in a real browser, detects all ad slots on the page, injects your own creative images into those slots, and captures a full-page screenshot — showing exactly how your ad would look in a real editorial environment.

---

## What it does

1. **Detect ad slots** — scans the live DOM using Google Publisher Tag (GPT) API, AdSense data attributes, and CSS heuristics to find every ad container on the page, including slots that are 0×0 (no real ad loaded yet).
2. **Inject creatives** — overlays your uploaded image onto each matching ad slot with pixel-accurate positioning.
3. **Screenshot** — captures the full page before and after injection so you can compare the original vs. simulated placement.
4. **Export** — generates a branded PowerPoint report with side-by-side before/after slides for client presentations.
5. **Mobile support** — runs a second pass in a 390×844 iPhone viewport with touch emulation for mobile-specific ad placements.

---

## Project structure

```
$Screenshot/
├── Backend_Screenshot/     # FastAPI backend — all scanning logic lives here
│   ├── main.py             # API entry point (FastAPI app)
│   ├── run.py              # Local dev server launcher
│   ├── render.yaml         # Render.com deployment config
│   ├── requirements.txt    # Python dependencies
│   ├── .env.example        # Environment variable template
│   ├── core/               # Config, auth, logging
│   ├── database/           # SQLAlchemy engine + session
│   ├── models/             # ORM models
│   ├── services/
│   │   ├── browser.py      # Playwright browser automation + injection engine
│   │   ├── ad_detector.py  # DOM scanner — GPT API, AdSense, CSS hints
│   │   ├── image_utils.py  # Creative matching (IAB size scoring)
│   │   ├── vision_detector.py   # Claude Vision fallback detection
│   │   ├── db_service.py   # DB read/write helpers
│   │   └── ppt_exporter.py # PowerPoint report generation
│   └── ppt_assets/         # Logo and background images for reports
├── Frontend_Screenshot/    # Frontend UI (served by FastAPI at /ui/)
├── input_images/           # Your creative images (uploaded via API)
│   ├── desktop/            # Desktop creatives (728×90, 300×250, 970×250 …)
│   └── mobile/             # Mobile creatives (320×50, 320×100, 300×250 …)
└── screenshots/            # Output screenshots (generated at runtime)
```

---

## Supported IAB ad sizes

| Size | Name |
|------|------|
| 728 × 90 | Leaderboard |
| 970 × 250 | Billboard |
| 300 × 250 | Medium Rectangle |
| 300 × 600 | Half Page |
| 160 × 600 | Wide Skyscraper |
| 468 × 60 | Full Banner |
| 320 × 50 | Mobile Banner |
| 320 × 100 | Mobile Large Banner |

---

## Getting started (local)

### Prerequisites
- Python 3.11+
- Node.js (optional, for frontend dev)

### Setup

```bash
cd Backend_Screenshot
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# Edit .env — set API_KEY, ANTHROPIC_API_KEY (optional)
```

### Run

```bash
python run.py
# API available at http://127.0.0.1:8001
# UI available at http://127.0.0.1:8001/ui/
```

---

## API overview

All endpoints (except `/health`) require the `X-API-Key` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/process` | Scan URLs and inject creatives (streaming NDJSON) |
| `GET` | `/results` | Fetch all scan results |
| `DELETE` | `/results/{id}` | Delete a result |
| `POST` | `/upload-creatives` | Upload creative images |
| `GET` | `/creatives` | List uploaded creatives |
| `DELETE` | `/delete-creative` | Delete a creative by filename |
| `POST` | `/results/export-ppt` | Export results as a PowerPoint report |

### Process request example

```json
POST /process
{
  "urls": ["https://example.com", "https://news.site.com"],
  "device": "desktop"
}
```

`device` is `"desktop"` (default) or `"mobile"`.

Response is a streaming NDJSON where each line is a JSON event (`progress`, `result`, `finished`, `error`).

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./scanner.db` | DB connection. Use `postgresql://...` on Render. |
| `API_KEY` | *(empty — disabled)* | Protects all API endpoints. |
| `ANTHROPIC_API_KEY` | *(empty)* | Claude Vision detection. Optional. |
| `ENGINE_CONCURRENCY` | `30` | Parallel browser tabs. Lower on small cloud instances. |
| `HEADLESS` | `true` | Run browser headless. Always `true` in production. |
| `APP_ENV` | `development` | `development` or `production`. |

---

## Deploying to Render

1. Push this repo to GitHub.
2. Go to [render.com](https://render.com) → **New Web Service** → connect your repo.
3. Render auto-detects `Backend_Screenshot/render.yaml` and configures everything.
4. Set `ANTHROPIC_API_KEY` manually in the Render dashboard (Environment tab).
5. *(Optional)* Add a Render PostgreSQL instance and set `DATABASE_URL` to the connection string — otherwise scan results are lost on restart.

The build command in `render.yaml` installs Playwright and Chromium automatically:
```
pip install -r requirements.txt && playwright install chromium && playwright install-deps chromium
```

> **RAM guide for `ENGINE_CONCURRENCY`:**
> Free tier (512 MB) → set to `3` · Starter (2 GB) → `8` · Standard (4 GB) → `20`

---

## Adding your creatives

Upload images via the API:

```bash
curl -X POST http://localhost:8001/upload-creatives \
  -H "X-API-Key: YOUR_KEY" \
  -F "files=@banner_728x90.png" \
  -F "files=@mrec_300x250.png"
```

Or place them directly in `input_images/desktop/` (or `input_images/mobile/`) and restart.

Name your files after their size for easy identification — e.g. `brand_728x90.png`, `brand_300x250.png`.

---

## License

Private — all rights reserved.
