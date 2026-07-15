# CMFS — Convention Management & Financial System

CMFS is the system built for the **Kenya Students' Christian Fellowship (KSCF)** to run its national, regional, and county conventions without the usual pile of Excel sheets, WhatsApp confirmations, and manual reconciliation at the gate.

It handles delegate registration and M-Pesa payments, QR-based check-in at the door, county-level budgeting, and the financial reports that get sent up the chain after every convention — across 47 counties and multiple regions, three times a year.

<img width="1892" height="916" alt="image" src="https://github.com/user-attachments/assets/babedb9c-afba-4d5c-b218-682c6ac14bc2" />


---

## Why this exists

KSCF conventions run three times a year — April, August, December — each about a week long, with registration open for months beforehand. A single convention can pull in close to 2,000 delegates spread across dozens of counties. Before this system, all of that — registration, cash and M-Pesa payments, who's actually shown up, what was budgeted versus what was spent — lived in spreadsheets that different people edited independently and someone had to reconcile by hand afterward.

CMFS replaces that with one system: delegates register and pay online, gate officials scan a QR code to check people in (even with a bad internet connection), and county/regional/national heads see live budget-vs-actual numbers instead of waiting for a report weeks later.

---

## How it's organized

Every convention has a **scope** — county, regional, or national — set once at creation and locked forever the moment it's published. Depending on scope, the system spins up one "Convention Unit" per county, per region, or a single national unit. Every delegate, payment, and expense belongs to exactly one unit, and unit data never crosses into another unit. A Nakuru county head cannot see Kericho's numbers, by design, not by convention.

Users aren't tied to a specific convention. They're tied to a **county or region**, permanently, from the moment they're invited. When a new convention is created that covers their geography, they get access automatically — no re-inviting the county head every April.

```
National
  └── Region (e.g. Rift Valley)
        └── County (47 total, e.g. Kericho)
              └── Delegate
```

### Roles

| Role | Scope | What they do |
|---|---|---|
| Super Admin | Everything | Creates conventions, invites heads, sees all data, resets TOTP for locked-out users |
| National Head | All regions/counties | National conventions — consolidated view, invites Regional Heads |
| Regional Head | Their region | Invites County Heads within the region |
| County Head | Their county | Invites Budget Creator, Finance Viewer, Gate Officials; runs county reports |
| Budget Creator | Their county | Enters budget estimates, actual expenses, manual delegate registration |
| Finance Viewer | Their county | Read-only access to financial data |
| Gate Official | Their county, active conventions only | Scans QR codes, marks attendance, takes cash at the gate |
| Delegate | Themselves | Registers, pays, checks balance and QR code |

A convention moves through a fixed sequence of states: `DRAFT → OPEN → ACTIVE → ENDED → FINANCIALLY_CLOSED → ARCHIVED`. Scope and fees can only be edited while a convention is still in DRAFT — the instant it's published (OPEN), that structure is locked at the database level and can't be changed, on purpose. Financial close is restricted to the Super Admin and National Head, and it's irreversible: once closed, nobody can add another expense line to that convention.

---

## What's actually in the app

**Registration & payments** — a public form (name, category, county/region, guardian phone for M-Pesa, email for the QR code) that triggers an M-Pesa STK Push on submit. A registration only becomes a real delegate — with an ID and QR code — once a payment actually confirms. Delegate IDs look like `KER-STU-2025-0042` (county, category, year, sequence). Budget Creators can also register someone manually, with cash or M-Pesa, for people who show up without registering online first.

**Gate check-in** — a lightweight PWA gate officials load on their phone. It pulls the county's full delegate list into memory once, so a QR scan is a local lookup, not a server round-trip — it works on bad venue wifi. It tracks online/offline state with a persistent banner, queues check-ins while offline, and syncs them one by one when the connection comes back, with an explicit warning before letting anyone log out with unsynced records still pending.

**Budgeting** — Budget Creators enter income and expense estimates before the convention, then log actual income and expenses (both budgeted line items and unbudgeted ones) as the convention runs. Everything rolls up automatically into variance figures.

**Financial reporting** — Excel and PDF reports generated on demand or automatically at key moments (opening day, convention end, financial close): income & expenditure statements, payment voucher logs, delegate registers, attendance reports, and an outstanding/written-off payments report. Reports can be pulled per county, consolidated per region, or national, and they're downloaded straight from the browser.

**Everything else** — audit logging on every write (append-only, nothing gets deleted or edited after the fact), TOTP two-factor auth for anyone handling money or admin functions, and an annual summary report that rolls up all three conventions in a year.

---

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Django + Django REST Framework |
| Database | PostgreSQL, with Row Level Security enforcing county/region isolation |
| Background jobs | Django Q2, using Postgres itself as the broker — no Redis, no Celery |
| Frontend | Next.js (React) + Tailwind CSS, with a PWA build for the gate app |
| Auth | JWT (short-lived access token + HttpOnly refresh cookie) + TOTP via `pyotp` |
| Payments | Safaricom M-Pesa Daraja API (STK Push + webhook callbacks) |
| Email | Resend |
| SMS | Africa's Talking, for critical alerts to Super Admin only |
| Reports | OpenPyXL (Excel), ReportLab (PDF) |
| File storage | Local filesystem under `/media/` — QR codes and generated reports |

Full dependency lists are in `cmfs_backend/requirements.txt` and `cmfs_frontend/package.json`.

---

## Security notes

A few things worth knowing before you run this anywhere near real data:

- **Row Level Security** is enforced at the Postgres level on delegates, payments, budgets, and attendance — not just in application code — so a bug in a view can't leak one county's data into another's.
- **Audit logs are insert-only.** There's a DB-level policy that blocks UPDATE and DELETE on the `audit_logs` table entirely.
- **TOTP is mandatory** for Super Admin, National Head, Regional Head, County Head, and Budget Creator. Gate Officials and Finance Viewers get away with a strong password only. Losing a TOTP device means using one of 8 one-time recovery codes issued at setup, the forgot-password flow (which resets TOTP too), or a Super Admin doing a confirmed reset.
- **The M-Pesa callback endpoint** only accepts requests from Safaricom's published IP range, on top of verifying the Daraja HMAC signature — both checks run before any payment logic executes.
- Every endpoint is rate-limited; login and password reset are limited harder than general traffic to blunt brute-force and email-bombing attempts.
- Nothing is hardcoded. All secrets come from environment variables, loaded via `python-decouple`.

---

## Getting it running locally

### Requirements

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- An M-Pesa Daraja sandbox account (only needed if you want to test payments)

### Backend

```bash
cd cmfs_backend
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Create a `.env` file in `cmfs_backend/` — see [Environment variables](#environment-variables) below for the full list.

```bash
python manage.py migrate
python manage.py seed_data              # loads the 47 counties + regions
python manage.py create_super_admin      # reads SUPER_ADMIN_EMAIL / SUPER_ADMIN_PASSWORD from .env
python manage.py setup_schedules         # registers the Django Q2 recurring tasks
python manage.py qcluster                # run in a separate terminal — this is the background worker
python manage.py runserver
```

`create_super_admin` prints the generated password once if you didn't set `SUPER_ADMIN_PASSWORD` yourself — TOTP is off for that account until you log in and set it up, so do that before touching anything else.

### Frontend

```bash
cd cmfs_frontend
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_URL` to wherever the backend is running (e.g. `http://localhost:8000`) in `cmfs_frontend/.env.local`.

### Environment variables

```
DJANGO_SECRET_KEY=
DEBUG=
DATABASE_URL=
ALLOWED_HOSTS=
NEXT_PUBLIC_API_URL=
FRONTEND_URL=
JWT_SECRET_KEY=
RESEND_API_KEY=
AFRICA_TALKING_USERNAME=
AFRICA_TALKING_API_KEY=
MPESA_CONSUMER_KEY=
MPESA_CONSUMER_SECRET=
MPESA_SHORTCODE=
MPESA_PASSKEY=
MPESA_CALLBACK_URL=
MPESA_IP_WHITELIST=
SUPER_ADMIN_EMAIL=
SUPER_ADMIN_PASSWORD=
```

`.env` is gitignored on purpose — don't commit real credentials, obviously, but it's worth saying anyway since this handles real money.

---

## Project layout

```
cmfs/
├── cmfs_backend/
│   ├── auth_app/        # login, TOTP, password reset, user invites
│   ├── conventions/     # convention lifecycle, geography, units
│   ├── budget/           # income/expense estimates and actuals
│   ├── delegates/       # registration, delegate records, QR generation
│   ├── payments/        # M-Pesa integration, cash payments, webhooks
│   ├── gate/             # check-in endpoints for the gate PWA
│   ├── reports/         # report generation (xlsx/pdf) and dashboards
│   └── cmfs_backend/    # settings, URL routing, middleware
└── cmfs_frontend/
    ├── pages/            # Next.js pages — one folder per module, roughly mirroring the backend apps
    ├── lib/              # API client, auth hook, shared helpers
    └── styles/
```

---




# CMFS Phase 2 Completion + Phase 3 — Deployment Guide

## Summary of files

### PHASE 2 — 3 files to REPLACE

| Output file | Destination in your repo | Action |
|---|---|---|
| `P2_auth_app_views.py` | `cmfs/cmfs_backend/auth_app/views.py` | REPLACE |
| `P2_api_urls.py` | `cmfs/cmfs_backend/cmfs_backend/api_urls.py` | REPLACE |
| `P2_reset_password.js` | `cmfs/cmfs_frontend/pages/auth/reset-password.js` | REPLACE |

### PHASE 3 — 11 files to CREATE

| Output file | Destination in your repo | Action |
|---|---|---|
| `P3_conventions_models.py` | `cmfs/cmfs_backend/conventions/models.py` | REPLACE |
| `P3_conventions_serializers.py` | `cmfs/cmfs_backend/conventions/serializers.py` | CREATE |
| `P3_conventions_permissions.py` | `cmfs/cmfs_backend/conventions/permissions.py` | CREATE |
| `P3_conventions_views.py` | `cmfs/cmfs_backend/conventions/views.py` | CREATE |
| `P3_conventions_urls.py` | `cmfs/cmfs_backend/conventions/urls.py` | CREATE |
| `P3_conventions_tasks.py` | `cmfs/cmfs_backend/conventions/tasks.py` | CREATE |
| `P3_migration_0003.py` | `cmfs/cmfs_backend/conventions/migrations/0003_convention_lifecycle_fields.py` | CREATE |
| `P3_lib_conventions.js` | `cmfs/cmfs_frontend/lib/conventions.js` | CREATE |
| `P3_conventions_index.js` | `cmfs/cmfs_frontend/pages/conventions/index.js` | CREATE |
| `P3_conventions_new.js` | `cmfs/cmfs_frontend/pages/conventions/new.js` | CREATE |
| `P3_conventions_detail.js` | `cmfs/cmfs_frontend/pages/conventions/[id].js` | CREATE |

---

## Phase 2 — What was fixed

### 1. `auth_app/views.py` — REPLACE
- Added `UserListView` class (GET /api/users/)
  - Super Admin sees all users
  - Head roles (national_head, regional_head, county_head) see users within their scope
  - Supports ?role=, ?county_id=, ?region_id=, ?convention_unit_id=, ?page= filters
- Added `@method_decorator(ratelimit, key='ip', rate='5/m')` to `PasswordResetConfirmView`
- Added `@method_decorator(ratelimit, key='ip', rate='60/m')` to `LogoutView`
- Fixed `PasswordResetConfirmView`: now correctly resets TOTP (sets `totp_secret=''`,
  `totp_enabled=False`) and deletes all recovery codes, per spec: *"user must re-setup
  Google Authenticator on next login"*. Returns `totp_reset: true` in response.

### 2. `api_urls.py` — REPLACE
- Added `path('users/', UserListView.as_view(), name='user-list')`
- Added `path('conventions/', include('conventions.urls'))` for Phase 3

### 3. `reset-password.js` — REPLACE
Full multi-step TOTP re-setup flow after password reset:
- **Step 'password'** — enter + confirm new password
- **Step 'totp_setup'** — auto-calls `/api/auth/totp/setup/` with post-reset token
- **Step 'qr'** — shows QR code to scan in Google Authenticator
- **Step 'recovery'** — shows 8 recovery codes with download button
- **Step 'verify_totp'** — user enters first 6-digit code to confirm setup
- **Step 'done'** — success message with sign-in link

---

## Phase 3 — What was built

### Backend
- **models.py** (REPLACE) — Convention: lifecycle timestamp fields
  (`scope_locked_at`, `published_at`, `started_at`, `ended_at`, `financially_closed_at`, `archived_at`).
  ConventionUnit: FK fields to County and Region, `created_at`, `unique_together` constraint.
- **serializers.py** (CREATE) — `ConventionListSerializer`, `ConventionDetailSerializer`,
  `ConventionCreateSerializer`, `ConventionUpdateSerializer`, `ConventionTransitionSerializer`,
  `CountySerializer`, `RegionSerializer`
- **permissions.py** (CREATE) — `IsSuperAdmin`, `IsHeadOrAbove`, `IsAuthenticated`,
  `user_can_view_convention()`, `user_can_manage_convention()`
- **views.py** (CREATE) — Full REST API:
  - `GET/POST /api/conventions/` — list + create
  - `GET/PATCH /api/conventions/<id>/` — detail + edit (DRAFT only)
  - `POST /api/conventions/<id>/publish/` — DRAFT → OPEN (scope lock)
  - `POST /api/conventions/<id>/activate/` — OPEN → ACTIVE
  - `POST /api/conventions/<id>/end/` — ACTIVE → ENDED
  - `POST /api/conventions/<id>/close/` — ENDED → FINANCIALLY_CLOSED (TOTP required)
  - `POST /api/conventions/<id>/archive/` — FINANCIALLY_CLOSED → ARCHIVED
  - `POST /api/conventions/<id>/opening-day-reports/` — trigger report generation
  - `GET /api/conventions/counties/` — county list for wizard
  - `GET /api/conventions/regions/` — region list for wizard
- **urls.py** (CREATE) — wires all convention URLs
- **tasks.py** (CREATE) — Django Q2 background tasks:
  - `auto_transition_convention_status()` — daily cron, auto-transitions on start/end dates
  - `send_convention_published_notifications(convention_id)`
  - `send_convention_started_notification(convention_id)`
  - `send_convention_ended_notification(convention_id)`
  - `generate_opening_day_reports(convention_id, triggered_by)`
  - `generate_final_reports(convention_id)` — stub, full implementation in Phase 10
- **migration 0003** (CREATE) — adds lifecycle fields + FK fields + DB triggers:
  - `enforce_convention_scope_lock` trigger (prevents scope/fee changes once locked)
  - `enforce_convention_unit_lock` trigger (prevents INSERT/DELETE on units once locked)

### Frontend
- **lib/conventions.js** (CREATE) — all API helpers + status constants, labels, colors,
  `getAvailableTransitions()` helper
- **pages/conventions/index.js** (CREATE) — list page with status filter tabs
- **pages/conventions/new.js** (CREATE) — 3-step creation wizard
- **pages/conventions/[id].js** (CREATE) — detail page with:
  - Lifecycle action buttons (role-scoped)
  - Publish confirmation modal (scope-lock warning)
  - Pre-close checklist modal
  - TOTP confirmation modal for financial close

---

## Post-deployment steps

### 1. Run the migration
```bash
cd cmfs/cmfs_backend
python manage.py migrate conventions
```

### 2. Schedule the daily cron task (Django Q2)
Add this to your settings or a management command:
```python
from django_q.models import Schedule

Schedule.objects.get_or_create(
    func='conventions.tasks.auto_transition_convention_status',
    defaults={
        'schedule_type': Schedule.DAILY,
        'name': 'Auto-transition convention status',
    }
)
```

### 3. Add RESEND_FROM_EMAIL to .env
```
RESEND_FROM_EMAIL=noreply@kscf.or.ke
```

### 4. The reset-password flow requires a `setup_access_token`
The backend's `PasswordResetConfirmView` currently returns `totp_reset: true` but does not
yet return a `setup_access_token`. You need to add this to the confirm view: after resetting
the password, issue a short-lived (5 min) access token scoped only to `/api/auth/totp/setup/`
and `/api/auth/totp/confirm/`, and return it as `setup_access_token` in the response. The
frontend reset-password.js is already wired to use it.

---

## Phase 3 Gate Tests — checklist

| # | Test | Status |
|---|---|---|
| 1 | POST /api/conventions/ → 201 + DRAFT | ✅ Implemented |
| 2 | GET /api/conventions/ → scoped by role | ✅ Implemented |
| 3 | PATCH /api/conventions/<id>/ in DRAFT → 200 | ✅ Implemented |
| 4 | PATCH /api/conventions/<id>/ after publish → 400 | ✅ Enforced in view + DB trigger |
| 5 | POST /api/conventions/<id>/publish/ → scope locked | ✅ Implemented |
| 6 | POST /api/conventions/<id>/activate/ → ACTIVE | ✅ Implemented |
| 7 | POST /api/conventions/<id>/end/ → ENDED + notifications | ✅ Implemented |
| 8 | POST /api/conventions/<id>/close/ without TOTP → 400 | ✅ Enforced |
| 9 | POST /api/conventions/<id>/close/ with valid TOTP → FINANCIALLY_CLOSED | ✅ Implemented |
| 10 | auto_transition_convention_status → activates on start_date | ✅ Task implemented |
| 11 | auto_transition_convention_status → ends on end_date | ✅ Task implemented |
| 12 | GET /api/users/ as Super Admin → all users | ✅ Implemented |
| 13 | GET /api/users/ as County Head → only county users | ✅ Implemented |
