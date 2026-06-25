#!/bin/bash
# ============================================================
# Creative Scanner Pro — Hostinger VPS Deploy Script
# Run this once as root (or sudo) on a fresh Ubuntu 22.04 VPS
# Usage: bash deploy.sh
# ============================================================

set -e

APP_DIR="/opt/creative-scanner"
REPO_URL="https://github.com/arunsagi98-sketch/-screenshot.git"
BACKEND_SUBDIR="Backend_Screenshot"
CONTAINER_NAME="creative-scanner-backend"
PORT=8000

echo "========================================"
echo " Creative Scanner Pro — VPS Setup"
echo "========================================"

# ── 1. System update ─────────────────────────────────────────
echo "[1/6] Updating system packages..."
apt-get update -y && apt-get upgrade -y

# ── 2. Install Docker ────────────────────────────────────────
echo "[2/6] Installing Docker..."
if ! command -v docker &>/dev/null; then
  apt-get install -y ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin
  systemctl enable docker
  systemctl start docker
  echo "Docker installed."
else
  echo "Docker already installed — skipping."
fi

# ── 3. Clone / update repo ───────────────────────────────────
echo "[3/6] Cloning repository..."
if [ -d "$APP_DIR" ]; then
  echo "Directory exists — pulling latest..."
  cd "$APP_DIR" && git pull
else
  git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR/$BACKEND_SUBDIR"

# ── 4. Create .env if it doesn't exist ───────────────────────
echo "[4/6] Checking .env..."
if [ ! -f ".env" ]; then
  echo ""
  echo "⚠️  No .env file found. Creating from template..."
  echo "   You MUST edit $APP_DIR/$BACKEND_SUBDIR/.env before the app will work!"
  cp .env.example .env
  echo ""
  echo "   Required values to set in .env:"
  echo "   DATABASE_URL      = your Railway PostgreSQL URL (scanner_db)"
  echo "   CRM_DATABASE_URL  = your Railway PostgreSQL URL (ctr_db)"
  echo "   API_KEY           = a strong random string"
  echo "   JWT_SECRET        = a strong random string"
  echo "   ALLOWED_ORIGINS   = https://your-netlify-app.netlify.app"
  echo ""
  echo "   Run: nano $APP_DIR/$BACKEND_SUBDIR/.env"
  echo "   Then re-run: bash $APP_DIR/hostinger_deploy/deploy.sh"
  exit 1
else
  echo ".env found — proceeding."
fi

# ── 5. Build Docker image ────────────────────────────────────
echo "[5/6] Building Docker image (this takes ~5 minutes first time)..."
docker build -t creative-scanner-backend .

# ── 6. Run container ─────────────────────────────────────────
echo "[6/6] Starting container..."

# Stop & remove old container if running
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true

docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  -p "$PORT:8000" \
  --env-file .env \
  -e APP_ENV=production \
  -e LOG_LEVEL=INFO \
  -e HEADLESS=true \
  -e ENGINE_CONCURRENCY=5 \
  -e ENGINE_NAV_TIMEOUT_MS=45000 \
  -v /opt/scanner-data:/app/data \
  creative-scanner-backend

echo ""
echo "========================================"
echo " ✅ Deployment complete!"
echo "========================================"
echo ""
echo " Backend is running at: http://$(curl -s ifconfig.me):$PORT"
echo " Health check:          http://$(curl -s ifconfig.me):$PORT/health"
echo ""
echo " View logs:    docker logs -f $CONTAINER_NAME"
echo " Stop server:  docker stop $CONTAINER_NAME"
echo " Restart:      docker restart $CONTAINER_NAME"
echo ""
echo " ⚠️  IMPORTANT: See HTTPS note in HOSTINGER_DEPLOY.md"
echo "    Your Netlify frontend needs HTTPS — set up Cloudflare Tunnel"
echo "    or point a domain to this server with SSL."
echo ""
