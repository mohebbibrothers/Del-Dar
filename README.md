# Del-Dar (دلدار) Backend Architecture & Gallery Platform

![Django](https://img.shields.io/badge/Django-5.1-092E20?style=for-the-badge&logo=django)
![DRF](https://img.shields.io/badge/DRF-Enterprise_API-ff1709?style=for-the-badge&logo=django)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Ready-316192?style=for-the-badge&logo=postgresql)
![Redis](https://img.shields.io/badge/Redis-State_Machine-dc382d?style=for-the-badge&logo=redis)
![Celery](https://img.shields.io/badge/Celery-Async_Queue-37814A?style=for-the-badge&logo=celery)
![Code Style: Ruff](https://img.shields.io/badge/Code%20Style-Ruff-000000?style=for-the-badge)

Enterprise-grade, highly optimized, API-first backend for **Del-Dar Photography Call for Entries & Virtual Gallery**.

---

## 🏗️ Architectural Overview & Core Engineering Highlights

The Del-Dar platform is built upon modern **Clean Architecture** principles, enforcing strict separation of concerns across domain entities, service layers, and infrastructure gateways:

1. **Redis-Backed Onboarding State Machine (`apps.onboarding`)**
   - Multi-step guest registration (Personal Info -> Supplementary Info -> Gallery Uploads).
   - Draft states are safely preserved inside Redis hashes keyed by a UUIDv4 token (`X-Draft-Token`) with a 24-hour TTL.
   - Eliminates incomplete/orphaned database records; atomic DB transactions (`transaction.atomic`) execute only upon successful OTP confirmation.

2. **Domain Entities & Strict Inspection (`apps.accounts`, `apps.works`)**
   - Custom User model (`AbstractBaseUser`) utilizing Iranian National Code (`national_code`) as the unique authentication identifier.
   - Algorithmic check-digit verification (Modulo 11) for Iranian National Codes.
   - In-memory `Pillow` inspection validating technical constraints prior to storage persistence:
     - Strict format whitelist: **JPEG / JPG only**.
     - Maximum payload limit: **5 MB per file**.
     - Dimension bounds: **1000px ≤ width, height <= 1500px**.
   - Hard business limit enforcement: Maximum 50 works total per photographer.

3. **Asynchronous Notification Gateway (`apps.sms`)**
   - Abstracted HTTP client connected to `api.iranpayamak.com` pattern endpoints.
   - Offloads OTP delivery and welcome dispatches to **Celery** workers backed by Redis broker.
   - Auto-mocking capabilities during test suites (`CELERY_TASK_ALWAYS_EAGER`) ensuring zero network latency.

4. **Memory-Safe Super Admin Backoffice (`apps.works.services`)**
   - Custom Django Admin actions enabling single & bulk user ZIP exports.
   - Archives are constructed on disk via stream chunks (`chunk_size=50`) preventing RAM buffer exhaustion (OOM) when exporting thousands of high-resolution 5MB photographs.
   - Automated Jalali (Solar Hijri) calendar formatting via `jdatetime` in exported `profile.txt` manifests.

---

## 🚀 Quickstart & Development Setup

### Prerequisites
- Python >= 3.13
- Redis Server (or SQLite local fallback)
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/mohebbibrothers/Del-Dar.git
cd Del-Dar
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run database migrations:
```bash
python manage.py migrate
```

4. Launch the local development server:
```bash
python manage.py runserver
```

### 📖 API Documentation (OpenAPI / Swagger UI)
Once running, interactive interactive API schemas are available at:
- **Swagger UI:** `http://127.0.0.1:8000/api/docs/`
- **OpenAPI Schema:** `http://127.0.0.1:8000/api/schema/`

---

## 🧪 Quality Assurance & Test Suites

The project strictly enforces **Zero Warnings & Zero Errors** policy validated by `ruff` and `pytest`.

```bash
# Run Django system inspection
python manage.py check

# Run extreme linter checks
ruff check .

# Execute full unit & integration test suite
pytest
```

---
*Architected and developed with elite senior engineering standards.*
