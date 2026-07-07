# راهنمای دیپلوی فرانت‌اند Del-Dar

فرانت‌اند React + Vite (Static SPA) است و روی `/var/www/deldar-frontend` سرو می‌شود.

##  Build محلی (توسعه)

```bash
cd /opt/deldar-frontend/src
npm install
npm run dev    # روی localhost:5173
```

## 🔧 vite.config.js

برای توسعه لوکال، proxy به بک‌اند production:

```js
server: {
  proxy: {
    "/api": {
      target: "https://ipcphotos.com",
      changeOrigin: true,
      secure: true,
    },
  },
}
```

**نکته مهم:** Nginx سرور هر دو مسیر `/api/...` و `/api/v1/...` را قبول می‌کند و مسیرهای `auth|onboarding|dashboard` را خودکار به `/api/v1/...` rewrite می‌کند. پس فرانت‌اند فقط `/api/...` می‌فرستد و Nginx بقیه کار را انجام می‌دهد.

##  آپدیت فرانت‌اند روی سرور

```bash
cd /opt/deldar-frontend/src
git pull origin master
npm install
npm run build
cp -r dist/* /var/www/deldar-frontend/
chown -R www-data:www-data /var/www/deldar-frontend
chmod -R 755 /var/www/deldar-frontend
```

##  ساختار

```
/var/www/deldar-frontend/
├── index.html
├── favicon.svg
├── icons.svg
└── assets/
    ├── index-*.js
    ├── index-*.css
    └── *.svg, *.png, *.ttf
```
