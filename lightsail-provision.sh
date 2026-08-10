#!/usr/bin/env bash
# Provision dedicated Inference Index public API + MCP on a fresh AWS Lightsail instance.
# Run as root (sudo). Idempotent. Illumina: run against the $10/mo Lightsail box.
set -euo pipefail

# ---------------------------------------------------------------
# 0. Config
# ---------------------------------------------------------------
# Set this to the read-only Supabase connection string for the PUBLIC API.
# Safer than reusing the scraper's full-role string. Rotate if ever leaked.
SUPABASE_DB_URL="${SUPABASE_DB_URL:?Set SUPABASE_DB_URL to a read-only Supabase conn string}"
DOMAIN="api.inferenceindexer.ai"
ACME_EMAIL="${ACME_EMAIL:-}"   # optional, for Let's Encrypt notifications

echo ">> Provisioning Inference Index public API on $(hostname)"

# ---------------------------------------------------------------
# 1. System packages
# ---------------------------------------------------------------
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-dev build-essential \
  nginx certbot python3-certbot-nginx git uvicorn >/dev/null

# ---------------------------------------------------------------
# 2. App user + code
# ---------------------------------------------------------------
APP_DIR="/opt/inferenceindexer"
mkdir -p "${APP_DIR}"
# Copy the API source onto the box (scp the repo, or clone):
# The public API only needs api.py + requirements. If the full repo is here, it
# must be sanitized (no scraper writes / no admin secrets).

# ---------------------------------------------------------------
# 3. Python venv + deps
# ---------------------------------------------------------------
cd "${APP_DIR}"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --quiet --upgrade pip
# Minimal deps for the read API (installed from the project source when present):
.venv/bin/pip install --quiet fastapi "uvicorn[standard]" psycopg2-binary httpx

# ---------------------------------------------------------------
# 4. Env (read-only DB conn string + SSR secret trusted tier)
# ---------------------------------------------------------------
cat > "${APP_DIR}/.env" <<EOF
SUPABASE_DB_URL=${SUPABASE_DB_URL}
X_SSR_SECRET=CHANGE_ME_ssr_secret
EOF
chmod 600 "${APP_DIR}/.env"

# ---------------------------------------------------------------
# 5. systemd service for the API
# ---------------------------------------------------------------
cat > /etc/systemd/system/inferenceindexer-api.service <<'EOF'
[Unit]
Description=InferenceIndexer public API (FastAPI/uvicorn)
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/inferenceindexer
EnvironmentFile=/opt/inferenceindexer/.env
ExecStart=/opt/inferenceindexer/.venv/bin/uvicorn api:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
EOF

# ---------------------------------------------------------------
# 6. nginx reverse proxy (http only; certbot upgrades to https)
# ---------------------------------------------------------------
cat > /etc/nginx/sites-available/inferenceindexer-api <<'EOF'
server {
    listen 80;
    server_name api.inferenceindexer.ai;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location /mcp {
        proxy_pass http://127.0.0.1:8899/mcp;
        proxy_http_version 1.1;
        proxy_set_header Host 127.0.0.1:8899;  # beat mcp dns-rebinding host check
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
ln -sf /etc/nginx/sites-available/inferenceindexer-api /etc/nginx/sites-enabled/inferenceindexer-api
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# ---------------------------------------------------------------
# 7. MCP server (install from the public GitHub repo)
# ---------------------------------------------------------------
if [ ! -d "${APP_DIR}/mcp-server" ]; then
  git clone https://github.com/DesMartin01/inferenceindexer-mcp "${APP_DIR}/mcp-server"
fi
cd "${APP_DIR}/mcp-server"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/pip install --quiet -e . || .venv/bin/pip install --quiet .

cat > /etc/systemd/system/inferenceindexer-mcp.service <<EOF
[Unit]
Description=InferenceIndexer MCP server (streamable-http)
After=network.target inferenceindexer-api.service

[Service]
Type=simple
User=www-data
WorkingDirectory=${APP_DIR}/mcp-server
EnvironmentFile=${APP_DIR}/.env
Environment=II_API_BASE=http://127.0.0.1:8000
ExecStart=${APP_DIR}/mcp-server/.venv/bin/inferenceindexer-mcp --transport streamable-http
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF

# ---------------------------------------------------------------
# 8. Enable + start services
# ---------------------------------------------------------------
systemctl daemon-reload
systemctl enable --now inferenceindexer-api inferenceindexer-mcp 2>/dev/null || true
sleep 3
systemctl restart inferenceindexer-api 2>/dev/null || true
systemctl restart inferenceindexer-mcp 2>/dev/null || true

# ---------------------------------------------------------------
# 9. Let's Encrypt (once DNS points here + port 80 open)
# ---------------------------------------------------------------
echo ">> Services up. Now issue HTTPS:"
echo "   certbot --nginx -d ${DOMAIN} --non-interactive --agree-tos --redirect ${ACME_EMAIL:+--register-unsafely-without-email}"
echo "   (run manually once api.inferenceindexer.ai resolves to this Lightsail IP)"

echo ">> DONE. Verify: curl http://127.0.0.1/v1/models?limit=1"