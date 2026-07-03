#!/usr/bin/env bash
set -euo pipefail

# ============================================================
#  Del-Dar Production Deployment Script
#  Server: 188.253.2.86 | Domain: ipcphotos.com
# ============================================================

PROJECT_DIR="/opt/deldar"
PROJECT_USER="deldar"
PROJECT_GROUP="www-data"
DOMAIN="ipcphotos.com"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo ""
echo "=========================================="
echo "  Del-Dar — Production Deploy"
echo "=========================================="
echo ""

# ---- Step 1: System packages ----
log "Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq \
    python3.12 python3.12-venv python3.12-dev python3-pip \
    postgresql postgresql-contrib \
    redis-server \
    nginx \
    certbot python3-certbot-nginx \
    git curl build-essential libjpeg-dev zlib1g-dev

log "System packages installed."

# ---- Step 2: Create application user ----
if ! id "$PROJECT_USER" &>/dev/null; then
    useradd -r -s /bin/false -m -d /opt/deldar "$PROJECT_USER"
    log "User '${PROJECT_USER}' created."
else
    warn "User '${PROJECT_USER}' already exists."
fi

# ---- Step 3: PostgreSQL setup ----
log "Configuring PostgreSQL..."
systemctl enable --now postgresql

DB_NAME="deldar_db"
DB_USER="deldar_user"
DB_PASS="${DB_PASSWORD:-deldar_strong_2026!}"

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME};"

sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname = '${DB_USER}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"
sudo -u postgres psql -d "${DB_NAME}" -c "GRANT ALL ON SCHEMA public TO ${DB_USER};"
sudo -u postgres psql -d "${DB_NAME}" -c "ALTER USER ${DB_USER} CREATEDB;" 2>/dev/null || true

log "PostgreSQL configured: database=${DB_NAME}, user=${DB_USER}"

# ---- Step 4: Redis setup ----
log "Configuring Redis..."
systemctl enable --now redis-server
log "Redis is running."

# ---- Step 5: Project directory ----
log "Setting up project directory..."
mkdir -p "${PROJECT_DIR}/logs"
mkdir -p "${PROJECT_DIR}/media"
mkdir -p /run/deldar
mkdir -p /var/www/certbot

# If project already exists, pull latest
if [ -d "${PROJECT_DIR}/config" ]; then
    warn "Project exists. Pulling latest from git..."
    cd "${PROJECT_DIR}"
    sudo -u "$PROJECT_USER" git pull origin master || warn "Git pull failed (no remote?)"
else
    warn "Project directory is empty. Clone your repo here:"
    warn "  git clone https://github.com/mohebbibrothers/Del-Dar.git ${PROJECT_DIR}"
fi

# ---- Step 6: Virtual environment ----
log "Setting up Python virtual environment..."
cd "${PROJECT_DIR}"

if [ ! -d "venv" ]; then
    python3.12 -m venv venv
fi

./venv/bin/pip install --upgrade pip -q
./venv/bin/pip install -r deploy/production-requirements.txt -q

log "Python dependencies installed."

# ---- Step 7: .env file ----
if [ ! -f "${PROJECT_DIR}/.env" ]; then
    warn ".env file not found. Creating from template..."
    warn "IMPORTANT: Edit ${PROJECT_DIR}/.env and set proper values!"
    cp deploy/.env.production.example "${PROJECT_DIR}/.env"

    RANDOM_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" 2>/dev/null || \
        openssl rand -base64 50)
    sed -i "s|CHANGE_ME_TO_A_RANDOM_64_CHAR_STRING|${RANDOM_KEY}|" "${PROJECT_DIR}/.env"

    chown "${PROJECT_USER}:${PROJECT_GROUP}" "${PROJECT_DIR}/.env"
    chmod 600 "${PROJECT_DIR}/.env"
    log ".env created. SECRET_KEY auto-generated."
else
    warn ".env already exists. Skipping."
fi

# ---- Step 8: Django setup ----
log "Running Django migrations..."
cd "${PROJECT_DIR}"
sudo -u "$PROJECT_USER" DJANGO_SETTINGS_MODULE=config.settings.production ./venv/bin/python manage.py migrate --noinput

log "Collecting static files..."
sudo -u "$PROJECT_USER" DJANGO_SETTINGS_MODULE=config.settings.production ./venv/bin/python manage.py collectstatic --noinput

log "Creating superuser (if not exists)..."
sudo -u "$PROJECT_USER" DJANGO_SETTINGS_MODULE=config.settings.production ./venv/bin/python manage.py shell -c "
from apps.accounts.models import User
if not User.objects.filter(is_superuser=True).exists():
    print('NO_SUPERUSER')
else:
    print('SUPERUSER_EXISTS')
" 2>/dev/null || true

# ---- Step 9: Permissions ----
log "Setting permissions..."
chown -R "${PROJECT_USER}:${PROJECT_GROUP}" "${PROJECT_DIR}/media"
chown -R "${PROJECT_USER}:${PROJECT_GROUP}" "${PROJECT_DIR}/logs"
chown -R "${PROJECT_USER}:${PROJECT_GROUP}" "${PROJECT_DIR}/staticfiles" 2>/dev/null || true
chown -R "${PROJECT_USER}:${PROJECT_GROUP}" /run/deldar
chmod 775 "${PROJECT_DIR}/media"
chmod 775 "${PROJECT_DIR}/logs"
chmod 775 /run/deldar

# ---- Step 10: Systemd services ----
log "Installing systemd services..."
cp deploy/systemd/gunicorn.service /etc/systemd/system/deldar-gunicorn.service
cp deploy/systemd/celery.service /etc/systemd/system/deldar-celery.service

systemctl daemon-reload
systemctl enable deldar-gunicorn
systemctl enable deldar-celery

log "Starting services..."
systemctl restart deldar-gunicorn
systemctl restart deldar-celery

# ---- Step 11: Nginx (without SSL first) ----
log "Configuring Nginx (HTTP only for now)..."

# Stop anything on port 80 that's not nginx
systemctl stop nginx 2>/dev/null || true
fuser -k 80/tcp 2>/dev/null || true
sleep 1

# Temporary HTTP-only config for certbot
cat > /etc/nginx/sites-available/deldar <<'NGINX_HTTP'
server {
    listen 80;
    server_name ipcphotos.com www.ipcphotos.com;

    client_max_body_size 20M;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location /static/ {
        alias /opt/deldar/staticfiles/;
    }

    location /media/ {
        alias /opt/deldar/media/;
    }

    location / {
        proxy_pass http://unix:/run/deldar/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX_HTTP

ln -sf /etc/nginx/sites-available/deldar /etc/nginx/sites-enabled/deldar
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl start nginx

log "Nginx configured and started."

echo ""
echo "=========================================="
echo -e "  ${GREEN}HTTP deployment complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Verify site works:  curl -I http://ipcphotos.com"
echo "  2. Get SSL certificate:"
echo "     certbot --nginx -d ipcphotos.com -d www.ipcphotos.com"
echo "  3. After SSL, deploy full nginx config:"
echo "     cp ${PROJECT_DIR}/deploy/nginx/deldar.conf /etc/nginx/sites-available/deldar"
echo "     nginx -t && systemctl reload nginx"
echo "  4. Update .env: SECURE_SSL_REDIRECT=True"
echo "  5. Create superuser:"
echo "     cd ${PROJECT_DIR} && sudo -u deldar ./venv/bin/python manage.py createsuperuser"
echo ""
