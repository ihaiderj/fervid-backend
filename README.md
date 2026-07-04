# Fervid Backend

Django REST API + Django Admin backend for the **Fervid** medical representative mobile app. Replaces Supabase (PostgreSQL RPCs, Auth, Storage) with a secure server-side API.

## Stack

- Django 5.x + Django REST Framework
- JWT auth (`djangorestframework-simplejwt`)
- PostgreSQL (SQLite for local dev)
- Local or S3 file storage
- OpenAPI docs via `drf-spectacular`

## Quick Start (Local)

```bash
cd fervid-backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

**Default admin:** `admin@medpresent.com` / `admin123` (change in production)

- API: http://localhost:8000/api/
- Swagger: http://localhost:8000/api/docs/
- Django Admin: http://localhost:8000/admin/

## Docker

```bash
docker compose up --build
```

## API Response Format

All endpoints return a Supabase-compatible envelope:

```json
{ "success": true, "data": { ... } }
{ "success": false, "error": "message", "code": "ERROR_CODE" }
```

## Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login/` | Email + password → JWT tokens |
| POST | `/api/auth/refresh/` | Refresh access token |
| GET | `/api/auth/me/` | Current user profile |
| POST | `/api/sessions/register/` | Single-device session enforcement |

Include header: `Authorization: Bearer <access_token>`

## Key Endpoints

### Admin (`role=admin`)
- `GET /api/admin/dashboard/stats/`
- `GET /api/admin/mrs/?include_permissions=true`
- `POST /api/admin/mrs/`
- `GET /api/admin/brochures/?with_categories=true`
- `GET /api/admin/doctors/`
- `GET /api/admin/meetings/`

### MR (`role=mr`)
- `GET /api/mr/dashboard/stats/`
- `GET /api/mr/brochures/`
- `GET /api/mr/doctors/`
- `GET /api/mr/meetings/?include_notes=true`
- `POST /api/mr/meetings/{id}/followups/`
- `GET /api/mr/saved-brochures/`
- `PUT /api/mr/brochure-sync/`

### Offline Sync
- `POST /api/sync/push/` — batch create/update/delete from mobile queue
- `GET /api/sync/pull/?since=<ISO8601>` — changed records since timestamp
- `GET /api/sync/status/` — health check

Sync entity order: `doctors → meetings → meeting_notes → meeting_followups → saved_brochures → brochure_sync → activity_logs`

### File Upload (server-side only — no service role key in mobile)
- `POST /api/files/brochures/upload/`
- `GET /api/files/brochures/{id}/download/`
- `POST /api/files/doctor-photos/upload/`

## Models

UUID primary keys throughout for compatibility with existing Supabase data and mobile SQLite `server_id` fields.

Notable addition: **`meeting_followups`** table (gap in Supabase SQL, required by mobile app).

## Django Admin

Production-ready admin with:
- User/MR management with permission inlines
- Doctor assignments, meetings with slide notes & follow-ups
- Brochure upload, categories, analytics counters
- Activity log audit (read-only, CSV export)
- System settings key-value config
- Session force-logout
- Custom dashboard with stats cards

## Environment Variables

See `.env.example` for full list. Key vars:

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_ENGINE` | `sqlite` | `postgresql` for production |
| `STORAGE_BACKEND` | `local` | `s3` for cloud storage |
| `MAX_FILE_SIZE_MB` | `10` | Upload limit |
| `CORS_ALLOWED_ORIGINS` | Expo dev URLs | Mobile app origins |

## Mobile Integration

Replace Supabase client calls in `AdminService.ts` / `MRService.ts` with HTTP requests to these REST endpoints. Response shapes match existing TypeScript interfaces.

Remove `supabaseAdmin` (service role key) from the mobile client — all privileged operations (user creation, file upload) are now server-side.

## Project Structure

```
fervid-backend/
├── accounts/       # User, auth, sessions, MR permissions, admin/MR views
├── doctors/        # Doctors, assignments, photos
├── brochures/      # Brochures, categories, saved/sync, file upload
├── meetings/       # Meetings, slide notes, follow-ups
├── activity/       # Activity logs, system settings
├── sync/           # Offline sync push/pull
├── core/           # Response envelope, permissions, services
└── config/         # Settings, URLs
```
