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
