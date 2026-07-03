# 🚀 راهنمای دیپلوی Del-Dar روی سرور production

**سرور:** `188.253.2.86` | **دامنه:** `ipcphotos.com` | **یوزر:** `root`

---

## پیش‌نیازها (قبل از شروع)

### ۱. دامنه و DNS
مطمئن شو DNS رکورد `A` برای `ipcphotos.com` و `www.ipcphotos.com` به `188.253.2.86`指向 شده.

### ۲. پوش کدها به گیت‌هاب
قبل از دیپلوی، مطمئن شو آخرین نسخه کد روی گیت‌هاب پوش شده:
```bash
# روی سیستم لوکال (ویندوز)
cd C:\Users\User\OneDrive\Desktop\Del-Dar-master
git add .
git commit -m "chore: prepare for production deployment"
git push origin master
```

---

## مرحله ۱: اتصال به سرور و پاکسازی پورت ۸۰

```bash
# اتصال به سرور
ssh root@188.253.2.86

# بررسی چی روی پورت ۸۰ نشسته
ss -tlnp | grep :80
lsof -i :80

# اگر Apache هست:
systemctl stop apache2
systemctl disable apache2

# اگر Nginx قبلی هست:
systemctl stop nginx

# پاکسازی هر چیزی روی پورت ۸۰:
fuser -k 80/tcp
```

---

## مرحله ۲: آپدیت سیستم و نصب پیش‌نیازها

```bash
# آپدیت سیستم
apt-get update && apt-get upgrade -y

# نصب پکیج‌های ضروری
apt-get install -y \
    software-properties-common \
    curl \
    git \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    ufw
```

### نصب Python 3.12
```bash
add-apt-repository ppa:deadsnakes/ppa -y
apt-get update
apt-get install -y python3.12 python3.12-venv python3.12-dev
python3.12 --version
```

> اگر `add-apt-repository` یا PPA کار نکرد (مثلاً Ubuntu 24.04 که Python 3.12 پیش‌فرض دارد):
> ```bash
> python3 --version  # اگر 3.12+ بود، ادامه بده
> ```

---

## مرحله ۳: نصب و تنظیم PostgreSQL

```bash
apt-get install -y postgresql postgresql-contrib
systemctl enable --now postgresql

# ساخت دیتابیس و یوزر
sudo -u postgres psql <<EOF
CREATE DATABASE deldar_db;
CREATE USER deldar_user WITH PASSWORD 'Y0ur_Str0ng_P@ss_2026!';
GRANT ALL PRIVILEGES ON DATABASE deldar_db TO deldar_user;
\c deldar_db
GRANT ALL ON SCHEMA public TO deldar_user;
\q
EOF

# تست اتصال
sudo -u postgres psql -d deldar_db -c "SELECT version();"
```

> **نکته:** پسورد `Y0ur_Str0ng_P@ss_2026!` را در `.env` هم باید ست کنی.

---

## مرحله ۴: نصب Redis

```bash
apt-get install -y redis-server
systemctl enable --now redis-server

# تست
redis-cli ping
# باید PONG برگرداند
```

---

## مرحله ۵: ساخت یوزر و دایرکتوری پروژه

```bash
# یوزر مخصوص پروژه
useradd -r -s /bin/false -m -d /opt/deldar deldar

# دایرکتوری‌ها
mkdir -p /opt/deldar/logs
mkdir -p /opt/deldar/media
mkdir -p /run/deldar
mkdir -p /var/www/certbot
```

---

## مرحله ۶: کلون پروژه

```bash
cd /opt
git clone https://github.com/mohebbibrothers/Del-Dar.git deldar_tmp
# اگر /opt/deldar قبلاً وجود داره:
# rm -rf /opt/deldar

mv deldar_tmp/* deldar_tmp/.* deldar/ 2>/dev/null || mv deldar_tmp/* deldar/
rm -rf deldar_tmp

chown -R deldar:www-data /opt/deldar
```

---

## مرحله ۷: Virtual Environment و نصب پکیج‌ها

```bash
cd /opt/deldar

# ساخت venv
python3.12 -m venv venv

# آپگرید pip
./venv/bin/pip install --upgrade pip

# نصب پکیج‌های production
./venv/bin/pip install -r deploy/production-requirements.txt

# تست نصب
./venv/bin/python -c "import django; print(django.get_version())"
```

---

## مرحله ۸: فایل .env

```bash
cd /opt/deldar

# ساخت .env از روی نمونه
cp deploy/.env.production.example .env

# ویرایش .env
nano .env
```

**مقادیر حیاتی که باید تغییر بدهی:**
```ini
# حتماً عوض کن:
SECRET_KEY=<یک رشته رندوم ۶۴ کاراکتری>
DB_PASSWORD=Y0ur_Str0ng_P@ss_2026!

# همین مقادیر OK هستند:
ALLOWED_HOSTS=ipcphotos.com,www.ipcphotos.com,188.253.2.86
CORS_ALLOWED_ORIGINS=https://ipcphotos.com,https://www.ipcphotos.com
SECURE_SSL_REDIRECT=False   # فعلاً False (بعد از SSL=True می‌شود)
```

> برای ساخت SECRET_KEY:
> ```bash
> cd /opt/deldar && ./venv/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

**مجوزها:**
```bash
chown deldar:www-data /opt/deldar/.env
chmod 600 /opt/deldar/.env
```

---

## مرحله ۹: Django setup (migrate + collectstatic)

```bash
cd /opt/deldar

export DJANGO_SETTINGS_MODULE=config.settings.production

# تست settings
./venv/bin/python manage.py check --deploy

# اگر warning داد نگران نباش (SSL بعداً اضافه می‌شود)

# migration
sudo -u deldar ./venv/bin/python manage.py migrate

# collectstatic
sudo -u deldar ./venv/bin/python manage.py collectstatic --noinput

# ساخت superuser
sudo -u deldar ./venv/bin/python manage.py createsuperuser
```

---

## مرحله ۱۰: نصب Gunicorn

```bash
cd /opt/deldar
./venv/bin/pip install gunicorn
```

### تست Gunicorn:
```bash
cd /opt/deldar
sudo -u deldar DJANGO_SETTINGS_MODULE=config.settings.production \
    ./venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2

# در تب دیگر تست کن:
curl -I http://127.0.0.1:8000/api/docs/
# Ctrl+C برای توقف
```

---

## مرحله ۱۱: Systemd Services

```bash
# کپی فایل‌های service
cp /opt/deldar/deploy/systemd/gunicorn.service /etc/systemd/system/deldar-gunicorn.service
cp /opt/deldar/deploy/systemd/celery.service /etc/systemd/system/deldar-celery.service

# مجوزها
chown -R deldar:www-data /opt/deldar/media /opt/deldar/logs /run/deldar
chmod 775 /opt/deldar/media /opt/deldar/logs /run/deldar

# Reload و start
systemctl daemon-reload
systemctl enable --now deldar-gunicorn
systemctl enable --now deldar-celery

# بررسی وضعیت
systemctl status deldar-gunicorn
systemctl status deldar-celery
```

---

## مرحله ۱۲: Nginx (مرحله اول — فقط HTTP)

```bash
apt-get install -y nginx

# حذف default
rm -f /etc/nginx/sites-enabled/default

# کانفیگ HTTP (قبل از SSL)
cat > /etc/nginx/sites-available/deldar <<'EOF'
server {
    listen 80;
    server_name ipcphotos.com www.ipcphotos.com;

    client_max_body_size 20M;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location /static/ {
        alias /opt/deldar/staticfiles/;
        expires 30d;
        access_log off;
    }

    location /media/ {
        alias /opt/deldar/media/;
        expires 7d;
        access_log off;
    }

    location / {
        proxy_pass http://unix:/run/deldar/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
EOF

ln -sf /etc/nginx/sites-available/deldar /etc/nginx/sites-enabled/deldar

# تست و ریستارت
nginx -t
systemctl restart nginx
```

### تست:
```bash
curl -I http://ipcphotos.com
# باید 200 OK بدهد
```

---

## مرحله ۱۳: SSL با Certbot

```bash
apt-get install -y certbot python3-certbot-nginx

# دریافت SSL certificate
certbot --nginx -d ipcphotos.com -d www.ipcphotos.com

# ایمیل و قوانین را تایید کن
```

> اگر certbot ارور داد (مثلاً domain resolve نمی‌شود)، اول DNS را چک کن:
> ```bash
> dig ipcphotos.com
> dig www.ipcphotos.com
> ```

---

## مرحله ۱۴: فعال‌سازی HTTPS کامل

بعد از دریافت SSL:

```bash
# کانفیگ کامل Nginx (با HTTPS redirect)
cp /opt/deldar/deploy/nginx/deldar.conf /etc/nginx/sites-available/deldar

nginx -t
systemctl reload nginx

# فعال‌سازی SSL redirect در Django
nano /opt/deldar/.env
# تغییر: SECURE_SSL_REDIRECT=True

systemctl restart deldar-gunicorn
```

---

## مرحله ۱۵: Firewall

```bash
ufw allow 22/tcp     # SSH
ufw allow 80/tcp     # HTTP
ufw allow 443/tcp    # HTTPS
ufw --force enable
ufw status
```

---

## مرحله ۱۶: تست نهایی

```bash
# ۱. بررسی سرویس‌ها
systemctl status deldar-gunicorn
systemctl status deldar-celery
systemctl status nginx
systemctl status redis-server
systemctl status postgresql

# ۲. تست API
curl https://ipcphotos.com/api/docs/
curl https://ipcphotos.com/api/schema/

# ۳. تست onboarding
curl -X POST https://ipcphotos.com/api/v1/onboarding/step-1/ \
    -H "Content-Type: application/json" \
    -d '{"national_code":"0012345678","mobile":"09123456789","first_name":"test","last_name":"test","occupation":"test","birth_date":"1370-01-01"}'

# ۴. بررسی لاگ‌ها
tail -f /opt/deldar/logs/deldar.log
tail -f /opt/deldar/logs/gunicorn_error.log
journalctl -u deldar-gunicorn -f
```

---

## دستورات مدیریت (بعد از دیپلوی)

```bash
# ریستارت سرویس‌ها
systemctl restart deldar-gunicorn
systemctl restart deldar-celery
systemctl reload nginx

# مشاهده لاگ
tail -f /opt/deldar/logs/deldar.log
journalctl -u deldar-gunicorn -f

# migration جدید
cd /opt/deldar
sudo -u deldar ./venv/bin/python manage.py migrate

# collectstatic جدید
sudo -u deldar ./venv/bin/python manage.py collectstatic --noinput

# Django shell
sudo -u deldar ./venv/bin/python manage.py shell

# ایجاد superuser جدید
sudo -u deldar ./venv/bin/python manage.py createsuperuser
```

---

## آپدیت کد (بعد از تغییرات)

```bash
cd /opt/deldar
sudo -u deldar git pull origin master
./venv/bin/pip install -r deploy/production-requirements.txt
sudo -u deldar ./venv/bin/python manage.py migrate
sudo -u deldar ./venv/bin/python manage.py collectstatic --noinput
systemctl restart deldar-gunicorn
systemctl restart deldar-celery
```

---

## عیب‌یابی

| مشکل | راه‌حل |
|------|--------|
| `502 Bad Gateway` | `systemctl status deldar-gunicorn` — گاندیکران اجرا نشده |
| `DisallowedHost` | `.env` → `ALLOWED_HOSTS` را چک کن |
| `CSRF verification failed` | `CORS_ALLOWED_ORIGINS` را چک کن |
| `Database connection error` | PostgreSQL running + `.env` DB credentials |
| `Redis connection error` | `systemctl status redis-server` |
| Static files 404 | `python manage.py collectstatic --noinput` |
| Media upload fails | `chown -R deldar:www-data /opt/deldar/media && chmod 775 /opt/deldar/media` |
