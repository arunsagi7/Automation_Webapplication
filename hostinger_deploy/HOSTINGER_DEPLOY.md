# Migrate Backend: Render → Hostinger VPS

## What changes
| | Before | After |
|---|---|---|
| **Backend** | Render (Docker) | Hostinger VPS (Docker) |
| **Database** | Railway PostgreSQL | Railway PostgreSQL (unchanged) |
| **Frontend** | Netlify | Netlify (unchanged) |

---

## Step 1 — Create a new Hostinger VPS

1. Log in to [hpanel.hostinger.com](https://hpanel.hostinger.com)
2. Go to **VPS** → **Create new VPS**
3. Choose:
   - **OS**: Ubuntu 22.04
   - **Plan**: At least **2 GB RAM** (required for Playwright/Chromium)
4. Note the new server's **IP address** (e.g. `203.x.x.x`)

---

## Step 2 — SSH into the new VPS

```bash
ssh root@YOUR_NEW_VPS_IP
```

---

## Step 3 — Run the deploy script

Copy the script to the server and run it:

```bash
# On your local machine — upload the script
scp hostinger_deploy/deploy.sh root@YOUR_NEW_VPS_IP:/root/deploy.sh

# On the VPS — run it
chmod +x /root/deploy.sh
bash /root/deploy.sh
```

The script will:
- Install Docker
- Clone your GitHub repo
- Create a `.env` template and **stop** — asking you to fill it in

---

## Step 4 — Fill in production environment variables

On the VPS, edit the `.env` file:

```bash
nano /opt/creative-scanner/Backend_Screenshot/.env
```

Set these values (get them from your Railway dashboard):

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/scanner_db
CRM_DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/ctr_db
API_KEY=generate-a-strong-random-string
JWT_SECRET=generate-another-strong-random-string
ALLOWED_ORIGINS=https://your-app.netlify.app
APP_ENV=production
LOG_LEVEL=INFO
HEADLESS=true
ENGINE_CONCURRENCY=5
ENGINE_NAV_TIMEOUT_MS=45000
```

To generate `API_KEY` and `JWT_SECRET`:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Then **run the deploy script again**:
```bash
bash /root/deploy.sh
```

---

## Step 5 — Open the firewall port

On the VPS, allow port 8000:

```bash
ufw allow 8000/tcp
ufw enable
```

Test the health check:
```bash
curl http://YOUR_NEW_VPS_IP:8000/health
```

You should get: `{"status":"ok"}`

---

## ⚠️ Step 6 — HTTPS (Critical for Netlify)

Your Netlify frontend is served over **HTTPS**. Browsers **block HTTP requests** from HTTPS pages (mixed content policy). So `http://YOUR_IP:8000` will be blocked.

### Option A — Cloudflare Tunnel (Free, No Domain Needed) ✅ Recommended

This gives you a free persistent HTTPS URL like `https://xyz.cfargotunnel.com`.

On the VPS:
```bash
# Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
dpkg -i cloudflared.deb

# Authenticate (opens a browser link — paste it on your local machine)
cloudflared tunnel login

# Create a named tunnel
cloudflared tunnel create creative-scanner

# Route tunnel to your local backend
cloudflared tunnel route dns creative-scanner api.yourdomain.com
# OR for a free *.cfargotunnel.com URL, use a quick tunnel (temporary):
cloudflared tunnel --url http://localhost:8000
```

For a **permanent free tunnel** (recommended):
1. Go to [dash.cloudflare.com](https://dash.cloudflare.com) → Zero Trust → Networks → Tunnels
2. Create tunnel → Connect → Docker or Linux
3. Set Public Hostname → your subdomain
4. Set Service → `http://localhost:8000`

### Option B — Buy a cheap domain + Let's Encrypt SSL

1. Buy a domain (~$1/year at Namecheap or Hostinger)
2. Point an `A` record to your VPS IP
3. Install Nginx + Certbot:

```bash
apt install nginx certbot python3-certbot-nginx -y
certbot --nginx -d api.yourdomain.com
```

4. Add Nginx reverse proxy config:

```nginx
server {
    server_name api.yourdomain.com;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
    }
}
```

---

## Step 7 — Update frontend URLs

Once you have the final HTTPS URL (e.g. `https://api.yourdomain.com`), run the update script:

```bash
# On your local machine, inside the project folder
python hostinger_deploy/update_frontend_urls.py https://api.yourdomain.com
```

This replaces `https://creative-scanner-backend-2.onrender.com` in all frontend files and `netlify.toml`.

Then push to GitHub → Netlify auto-deploys.

---

## Step 8 — Update the keep-alive scheduled task

In Claude (Cowork), tell it:
> "Update the keep-alive ping URL to https://api.yourdomain.com/health"

---

## Step 9 — Verify everything works

1. Open your Netlify frontend
2. Login should work (hits backend auth)
3. Backend status badge should show **Online**
4. Run a test scan

---

## Useful VPS commands

```bash
# View live logs
docker logs -f creative-scanner-backend

# Restart backend
docker restart creative-scanner-backend

# Redeploy after code changes
cd /opt/creative-scanner && git pull
cd Backend_Screenshot && docker build -t creative-scanner-backend .
docker restart creative-scanner-backend

# Check container status
docker ps
```
