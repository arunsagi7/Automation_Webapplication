# Deployment Guide — Creative Scanner Pro

Architecture: **Netlify (frontend) → Render (backend) → Railway (PostgreSQL)**

---

## Step 1 — Railway: Create two PostgreSQL databases

1. Go to [railway.app](https://railway.app) → New Project → Add PostgreSQL
2. Name it `scanner-db` → copy the **connection string** (Postgres URL)
3. Add another PostgreSQL service → name it `ctr-db` → copy its connection string
4. Keep both strings handy for Step 2.

---

## Step 2 — Render: Deploy the backend

1. Push your code to GitHub (make sure `Backend_Screenshot/Dockerfile` is committed)
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Set **Root Directory** to `Backend_Screenshot`
5. Render will auto-detect the Dockerfile
6. Choose **Standard** plan ($25/month) — Playwright needs 2 GB RAM
7. Set these **Environment Variables** in the Render dashboard:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | Railway scanner-db connection string |
| `CRM_DATABASE_URL` | Railway ctr-db connection string |
| `API_KEY` | Any strong random string (e.g. run: `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `APP_ENV` | `production` |
| `ALLOWED_ORIGINS` | `https://YOUR-APP.netlify.app` (fill in after Step 3) |
| `ANTHROPIC_API_KEY` | Optional — Claude Vision key |
| `HEADLESS` | `true` |
| `ENGINE_CONCURRENCY` | `5` |

8. Add a **Disk** in Render: mount path `/app/data`, size 5 GB
9. Click **Deploy** — first deploy takes ~5 minutes (Chromium install)
10. Copy your Render URL: `https://creative-scanner-pro.onrender.com`

---

## Step 3 — Frontend: Update the backend URL

In every `.html` file in `Frontend_Screenshot/`, find this line and replace the placeholder:

```html
window.API_BASE_URL = "https://YOUR-APP.onrender.com";
```

Replace with your actual Render URL, e.g.:
```html
window.API_BASE_URL = "https://creative-scanner-pro.onrender.com";
```

Files to update:
- `index.html`
- `crm-excel.html`
- `ppt-store.html`
- `final-report.html`
- `qc-checker.html`
- `reach-report.html`
- `login.html`

Also update `netlify.toml` — replace `YOUR-APP.onrender.com` with your actual Render URL.

---

## Step 4 — Netlify: Deploy the frontend

1. Go to [netlify.com](https://netlify.com) → Add new site → Import from Git
2. Connect your GitHub repo
3. Set **Base directory** to `Frontend_Screenshot`
4. **Publish directory**: `.` (dot — the Frontend_Screenshot folder itself)
5. Click **Deploy**
6. Copy your Netlify URL: `https://your-app.netlify.app`

---

## Step 5 — Wire everything together

1. Back in **Render Dashboard** → Environment → set `ALLOWED_ORIGINS` to your Netlify URL
2. Trigger a **Manual Deploy** in Render so the new CORS setting takes effect
3. Open your Netlify URL in the browser — everything should work

---

## Step 6 — Add your API key to the frontend

The frontend needs to send the `X-Api-Key` header. Check your frontend config or login flow to make sure the API key set in Render matches what the frontend sends.

---

## Persistent file storage (screenshots / uploads / processed CSVs)

The Render disk is mounted at `/app/data`. Set these env vars in Render so files survive restarts:

| Env var | Value |
|---------|-------|
| `SCREENSHOTS_DIR` | `/app/data/screenshots` |
| `INPUT_IMAGES_DIR` | `/app/data/input_images` |
| `PROCESSED_OUTPUTS_DIR` | `/app/data/processed_outputs` |

Without these, CRM processed CSVs and screenshots will be lost every time Render restarts the service.

---

## Quick reference

| Service | URL |
|---------|-----|
| Backend API | `https://creative-scanner-pro.onrender.com` |
| API Docs (Swagger) | `https://creative-scanner-pro.onrender.com/docs` |
| Frontend | `https://your-app.netlify.app` |
| Railway DB dashboard | [railway.app](https://railway.app) |
