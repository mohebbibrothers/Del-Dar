# پروژه بک‌اند «دلدار» (Del-Dar Platform)

![Django](https://img.shields.io/badge/Django-5.1-092E20?style=for-the-badge&logo=django)
![DRF](https://img.shields.io/badge/DRF-Enterprise_API-ff1709?style=for-the-badge&logo=django)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Ready-316192?style=for-the-badge&logo=postgresql)
![Redis](https://img.shields.io/badge/Redis-State_Machine-dc382d?style=for-the-badge&logo=redis)
![Celery](https://img.shields.io/badge/Celery-Async_Queue-37814A?style=for-the-badge&logo=celery)
![Code Style: Ruff](https://img.shields.io/badge/Code%20Style-Ruff-000000?style=for-the-badge)

سامانه جامع، استاندارد و بسیار بهینهٔ **فراخوان عکاسی و گالری مجازی دلدار** مبتنی بر معماری سرویس‌گرا (API-First).

---

## 🏗️ معماری مهندسی و ویژگی‌های برجسته فنی

پروژه «دلدار» با تکیه بر اصول مدرن **Clean Architecture** و رعایت دقیق تفکیک لایه‌ها (Separation of Concerns) طراحی شده است:

1. **ماشین حالت ثبت‌نام چندمرحله‌ای بر پایه Redis (`apps.onboarding`)**
   - پیاده‌سازی چرخه ثبت‌نام کاربر مهمان در سه فاز متوالی (اطلاعات شخصی -> اطلاعات تکمیلی -> آپلود آثار).
   - تمام داده‌ها و پیش‌نویس‌ها بدون آلوده کردن پایگاه داده اصلی، درون کش **Redis Hash** با شناسه‌ای یکتا به نام `X-Draft-Token` (تولیدشده توسط UUIDv4) و طول عمر ۲۴ ساعته نگهداری می‌شوند.
   - فقط زمانی که کاربر پیامک تایید (OTP) را با موفقیت وارد کند، تراکنش اتمیک پایگاه داده (`transaction.atomic`) فعال شده و پروفایل کاربر به همراه آثارش به صورت قطعی ثبت می‌گردد.

2. **هسته سفارشی کاربران و ولیدیتورهای سطح حافظه (`apps.accounts` و `apps.works`)**
   - پیاده‌سازی Custom User Model بر پایه `AbstractBaseUser` با تنظیم فیلد `USERNAME_FIELD` روی کدملی یکتا (`national_code`).
   - الگوریتم ریاضی کنترل‌رقم (Check Digit مدول ۱۱) جهت اعتبارسنجی کدهای ملی ایران.
   - بازرسی فنی تصاویر در حافظه RAM توسط کتابخانه `Pillow` قبل از ذخیره روی دیسک با ۳ شرط سخت‌گیرانه:
     1. فرمت فایل صرفاً باید **JPG / JPEG** باشد.
     2. حجم هر فایل نباید از **۵ مگابایت** تجاوز کند.
     3. ابعاد تصویر (عرض و ارتفاع) باید دقیقاً بین **۱۰۰۰ تا ۱۵۰۰ پیکسل** باشد.
   - اعمال محدودیت بیزینسی حداکثر **۵۰ اثر** برای هر هنرمند.

3. **لایه سرویس پیامک و پردازش غیرهمزمان (`apps.sms`)**
   - یکپارچه‌سازی کلاینت HTTP با درگاه `api.iranpayamak.com` جهت ارسال پترن‌های کد تایید و خوش‌آمدگویی.
   - واگذاری کامل ارسال پیامک‌ها به کارگزار **Celery** و **Redis** جهت جلوگیری از کند شدن پاسخ‌دهی APIها.

4. **موتور اکسپورت ادمین ضدِ هنگ (`apps.works.services`)**
   - اکشن‌های تقویت‌شده در پنل ادمین جنگو جهت دانلود خروجی ZIP تک‌کاربره و گروهی.
   - جهت جلوگیری از خطای کمبود حافظه (Out of Memory) در زمان دانلود هزاران عکس ۵ مگابایتی، آرشیو زیپ به صورت استریم‌شده و تکه‌تکه (`Chunked`) روی دیسک ساخته می‌شود.
   - تبدیل تقویم میلادی به **شمسی (جلالی)** توسط `jdatetime` در فایل‌های متنیِ `profile.txt` هر هنرمند.

---

## 🚀 راهنمای راه‌اندازی سریع پروژه (توصیه‌شده با Virtualenv)

جهت جلوگیری از تداخل پکیج‌های پایتون سیستم عامل، پیشنهاد می‌شود پروژه را درون محیط مجازی اجرا کنید:

### ۱. دریافت سورس کد
```bash
git clone https://github.com/mohebbibrothers/Del-Dar.git
cd Del-Dar
```

### ۲. ساخت و فعال‌سازی محیط مجازی (Virtual Environment)

**در لینوکس و مک:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**در ویندوز (CMD / PowerShell):**
```bash
python -m venv venv
venv\Scripts\activate
```

### ۳. نصب وابستگی‌ها
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### ۴. اجرای مایگریشن‌های پایگاه داده
```bash
python manage.py migrate
```

### ۵. اجرای سرور توسعه محلی
```bash
python manage.py runserver
```

*(سرور روی آدرس `http://127.0.0.1:8000` در دسترس خواهد بود).*

---

## 📖 مستندات جامع API برای توسعه‌دهندگان فرانت‌اند (Swagger UI)

تمامی اندپوینت‌های پروژه مجهز به **مثال‌های دقیق درخواست (Example Value)**، **نمونه پاسخ‌ها (Example Response)** و توضیحات فارسی کامل هستند. پس از اجرای پروژه، جهت مشاهده و تست آنلاین APIها به لینک‌های زیر مراجعه کنید:

- **رابط تعاملی Swagger UI:**  
  `http://127.0.0.1:8000/api/docs/`
- **خروجی خام OpenAPI JSON:**  
  `http://127.0.0.1:8000/api/schema/`

---

## 🧪 اجرای تست‌های خودکار و تضمین کیفیت

پروژه بر اساس استاندارد **Zero Warning & Zero Error** توسعه یافته است:

```bash
# بررسی سلامت ساختار جنگو
python manage.py check

# اجرای بررسی‌های دقیق سبک کد (Linter)
ruff check .

# اجرای مجموعه تست‌های جامع واحد و یکپارچه
pytest
```

---
*توسعه‌یافته با بالاترین استانداردهای معماری نرم‌افزار.*
