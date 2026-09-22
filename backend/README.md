# Backend (FastAPI)

API for autonomous vehicle job profiles.

## Requirements

- Python 3.10+
- PostgreSQL 14+ (local install)
- Packages in `requirements.txt`

## Setup

### 1. PostgreSQL (required first)

Install and start PostgreSQL (Ubuntu/Debian):

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

Create the database user and database (run as the `postgres` system user):

```bash
sudo -u postgres psql
```

In the `psql` shell:

```sql
CREATE USER team3 WITH PASSWORD '<password>';
CREATE DATABASE autojobdatabase OWNER team3;
GRANT ALL PRIVILEGES ON DATABASE autojobdatabase TO team3;
\q
```

On PostgreSQL 15+, also grant schema access:

```bash
sudo -u postgres psql -d autojobdatabase -c "GRANT ALL ON SCHEMA public TO team3;"
```

Confirm the connection (default local port is `5432`):

```bash
psql -h localhost -p 5432 -U team3 -d autojobdatabase
```

#### Optional: Docker instead of a local install

If you prefer Docker:

```bash
docker run -d --name autojob-pg \
  -e POSTGRES_USER=team3 \
  -e POSTGRES_PASSWORD='<password>' \
  -e POSTGRES_DB=autojobdatabase \
  -p 5433:5432 \
  postgres:14
```

Then use port `5433` in `.env` (see below). Later starts: `docker start autojob-pg`.

### 2. Python environment

```bash
cd backend
pip install -r requirements.txt
```

Copy the sample env file, then set values to match your Postgres instance:

```bash
cp .env.sample .env
```

`.env.sample` is the template. Your local `.env` (gitignored) is what the app reads.

Example for a manual local install (port `5432`):

```env
DATABASE_URL=postgresql://team3:<password>@localhost:5432/autojobdatabase
DATABASE_USER=team3
DATABASE_PASSWORD=<password>
SEED_ON_STARTUP=false
JWT_SECRET_KEY=<generate-a-long-random-secret>
AUTH_COOKIE_SECURE=false
```

Use the same password you set when creating the Postgres user. If you used the Docker option above, use port `5433` instead.

Keep `SEED_ON_STARTUP=false` (see `.env.sample`): `true` reseeds companies on *every* API start via `app/sql/seed_companies.sql`, which opens with `TRUNCATE TABLE company CASCADE` - that cascades through the FK graph and wipes every jobposting (Silver-synced categories, skills, and salary data included) down to the 12 hardcoded demo postings. Only set it `true` for a genuine from-scratch reseed on a database you don't mind emptying.

Generate `JWT_SECRET_KEY` with a cryptographically secure random generator and
keep it outside source control. Set `AUTH_COOKIE_SECURE=true` when the frontend
and API are served over HTTPS. Any environment other than an explicitly named
`development` environment fails at startup when `JWT_SECRET_KEY` is missing or
blank. An unset or blank `ENVIRONMENT` does not enable development mode. To use
the local fallback explicitly, set `ENVIRONMENT=development`; otherwise provide
a real signing key. CI uses a freshly generated test-only key.

### CI note

Backend CI starts an ephemeral Postgres service with `POSTGRES_HOST_AUTH_METHOD=trust` (no password). That is for GitHub Actions only — local Postgres should still use a password in `.env`.

## Run

From the `backend/` directory (Postgres must already be running):

```bash
python3 -m uvicorn app.main:app --reload
```

On startup the API:

1. Creates tables if they do not exist
2. If `SEED_ON_STARTUP=true`, reseeds the company list from `app/sql/seed_companies.sql`

The API listens on [http://127.0.0.1:8000](http://127.0.0.1:8000).

| URL | Description |
|---|---|
| http://127.0.0.1:8000/docs | Swagger UI |
| http://127.0.0.1:8000/redoc | ReDoc |
| http://127.0.0.1:8000/health | Health check |
| http://127.0.0.1:8000/api/v1/companies | Companies API |
| http://127.0.0.1:8000/api/v1/auth/signup | Account registration |
| http://127.0.0.1:8000/api/v1/auth/login | JWT sign in |
| http://127.0.0.1:8000/api/v1/auth/me | Current authenticated user |
| http://127.0.0.1:8000/api/v1/auth/forgot-password | Request a password-reset email |
| http://127.0.0.1:8000/api/v1/auth/reset-password | Complete a forgotten-password reset |
| http://127.0.0.1:8000/api/v1/favorites/jobs | Current user's favorite jobs |
| http://127.0.0.1:8000/api/v1/favorites/companies | Current user's favorite companies |

## Authentication API

Passwords must contain at least 12 characters, including uppercase, lowercase,
a number, and a special character. Passwords are stored as Argon2 hashes. The
signed JWT contains only the user ID, token type, session version, issued-at
time, and expiry and is returned in an HTTP-only `SameSite=Lax` cookie rather
than response JSON.

The login identifier accepts either the normalized email address or username.
Five failed attempts for the same client and identifier within five minutes are
rate limited by default; both values can be changed with
`AUTH_LOGIN_MAX_ATTEMPTS` and `AUTH_LOGIN_WINDOW_SECONDS`.

The included limiter stores counters in the current API process. This is
appropriate for local development and single-worker deployments. Production
deployments with multiple workers or instances must use a shared store such as
Redis so failed-login counters are enforced consistently across processes.

### Sign up

```bash
curl -i -c cookies.txt -X POST http://127.0.0.1:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "driver@example.com",
    "username": "driver_engineer",
    "full_name": "Driver Engineer",
    "password": "SecurePassword!123"
  }'
```

### Sign in and access a protected endpoint

```bash
curl -i -c cookies.txt -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "driver@example.com",
    "password": "SecurePassword!123",
    "remember_me": false
  }'

curl -b cookies.txt http://127.0.0.1:8000/api/v1/auth/me
```

### Forgotten-password reset (BE-20)

The forgotten-password flow uses opaque, single-use tokens. Only a SHA-256 hash
of each token is stored, and tokens expire after 20 minutes by default. The
request endpoint always returns the same `202` response for known and unknown
identifiers to prevent account enumeration.

| Method | URL | Result |
|---|---|---|
| `POST` | `/api/v1/auth/forgot-password` | Request a reset email using an email or username |
| `GET` | `/api/v1/auth/reset-password/verify?token=...` | Check whether a token is valid and unused |
| `POST` | `/api/v1/auth/reset-password` | Consume a token and set a policy-compliant password (`204`) |

Request a reset:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"identifier": "driver@example.com"}'
```

The email link points to `PASSWORD_RESET_FRONTEND_URL` and includes the opaque
token as its `token` query parameter. The frontend can verify that token before
showing the form, then submit it with the new password:

```bash
curl "http://127.0.0.1:8000/api/v1/auth/reset-password/verify?token=<token>"

curl -i -X POST http://127.0.0.1:8000/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "<token>",
    "new_password": "UpdatedPassword!456"
  }'
```

A successful reset immediately marks every outstanding reset token for that
user as used and increments the user's token version. This invalidates all
previously issued login cookies and bearer tokens; the user must sign in again.
A password-changed confirmation email is also sent. Expired, used, and unknown
reset tokens return explicit `400` errors, while malformed input and weak
passwords return validation errors.

Configure email delivery and reset controls in `.env`:

```dotenv
PASSWORD_RESET_TOKEN_MINUTES=20
PASSWORD_RESET_MAX_REQUESTS=5
PASSWORD_RESET_WINDOW_SECONDS=900
PASSWORD_RESET_FRONTEND_URL=http://localhost:5173/reset-password
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=example-user
SMTP_PASSWORD=example-password
SMTP_FROM_EMAIL=no-reply@example.com
SMTP_STARTTLS=true
```

`PASSWORD_RESET_TOKEN_MINUTES` must stay between 15 and 30. Reset requests are
limited independently by hashed identifier and client IP. Like the existing
login limiter, the bundled limiter is process-local; use a shared store such as
Redis when running multiple API instances. Logs contain user IDs or hashed
request keys, never raw reset tokens or passwords.

Fresh databases receive the table and token-version column through ORM startup.
For an existing PostgreSQL database, apply the repeatable migration from
`backend/`:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f app/sql/be20_password_reset_migration.sql
```

## Favorites API (BE-11)

All favorite endpoints require a valid login cookie or bearer token. The user ID
comes from the authenticated session, not from a client-supplied parameter.

| Method | URL | Result |
|---|---|---|
| `GET` | `/api/v1/favorites/jobs` | Current user's favorite jobs with live job details |
| `POST` | `/api/v1/favorites/jobs/{job_id}` | Add a job favorite (`201`) |
| `DELETE` | `/api/v1/favorites/jobs/{job_id}` | Remove a job favorite (`204`) |
| `GET` | `/api/v1/favorites/companies` | Current user's favorite companies with live company details |
| `POST` | `/api/v1/favorites/companies/{company_id}` | Add a company favorite (`201`) |
| `DELETE` | `/api/v1/favorites/companies/{company_id}` | Remove a company favorite (`204`) |

The list responses are arrays. Each job entry has `job_id`, `created_at`, and a
`job` object using the normal `JobResponse` fields. Each company entry has
`company_id`, `created_at`, and a `company` object using `CompanyResponse`.
Repeated adds return `409`, missing targets or missing favorites return `404`,
and unauthenticated requests return `401`. Invalid UUIDs return `422`.

For example, after login:

```bash
curl -b cookies.txt -X POST \
  http://127.0.0.1:8000/api/v1/favorites/jobs/<job_uuid>
curl -b cookies.txt http://127.0.0.1:8000/api/v1/favorites/jobs
curl -b cookies.txt -X DELETE \
  http://127.0.0.1:8000/api/v1/favorites/jobs/<job_uuid>
```

Fresh databases receive the two tables through the normal ORM startup path.
For an existing PostgreSQL backend, apply `app/sql/be11_favorites_migration.sql`
after the authentication tables exist; the migration can be run more than once.
From `backend/`, the command is:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f app/sql/be11_favorites_migration.sql
```

Its composite primary keys prevent duplicates, and its foreign keys remove
favorites when a user, job, or company is hard-deleted. The list queries join to
live targets and eagerly load job relations to avoid per-item queries.

The current job and company schemas have no archived-state field. This API
therefore handles hard-deleted records, but it cannot distinguish archived
targets until the team defines and persists an archive status. Also keep
`SEED_ON_STARTUP=false` when testing persistence: the legacy development seed
uses `TRUNCATE company CASCADE`, which intentionally removes company-linked
data, including favorites.

The optional PostgreSQL migration regression runs only against an explicitly
named test database: set `BE11_TEST_POSTGRES=1` and `BE11_TEST_DATABASE_URL`,
then run `pytest tests/integration_test/test_favorites_postgres_migration.py`.
The test creates and removes its own uniquely named schema.

## Companies API (testing)

### List companies

```bash
curl http://127.0.0.1:8000/api/v1/companies
```

### Get company by id

```bash
curl http://127.0.0.1:8000/api/v1/companies/11111111-1111-1111-1111-111111111035
```

### Create a company

```bash
curl -X POST http://127.0.0.1:8000/api/v1/companies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Example AV Co",
    "website_url": "https://example-av.example",
    "career_page_url": "https://example-av.example/careers",
    "company_type": "AV_Startup",
    "datasource_status": "confirmed"
  }'
```

Note: when `SEED_ON_STARTUP=true`, created rows are replaced on restart because startup reseeds from the SQL file.

### Company descriptions

`CompanyResponse.description` is a short "About" blurb shown on the company
profile page. Apply the repeatable migration to an existing database before
it will populate:

```bash
psql "$DATABASE_URL" -f app/sql/company_description_migration.sql
```

## Job management API (BE-19)

Apply the repeatable migration to an existing backend database and configure a
server-to-server write key:

```bash
psql "$DATABASE_URL" -f app/sql/be19_job_details_migration.sql
```

```env
JOB_WRITE_API_KEY=<generate-a-long-random-secret>
```

The BE-19 write source is a single system API request. Scheduled bulk ingestion
continues to use `python -m app.sync_silver`. A caller-supplied `source_key` is
stored in the isolated `api:` namespace; reusing it returns `409 Conflict`.

Existing locations, skills, and categories can be linked by their ID fields.
New values can be created atomically with the job through the nested
`locations`, `skills`, and `categories` fields:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -H "X-Job-Write-Key: $JOB_WRITE_API_KEY" \
  -d '{
    "source_key": "waymo-engineer-123",
    "company_id": "11111111-1111-1111-1111-111111111035",
    "title": "Robotics Software Engineer",
    "description": "Build autonomous driving software.",
    "requirements": "Python, C++, and robotics experience.",
    "posted_date": "2026-09-21T08:00:00Z",
    "salary_min": 140000,
    "salary_max": 180000,
    "salary_currency": "USD",
    "salary_period": "yearly",
    "salary_source": "api",
    "locations": ["Mountain View, CA"],
    "skills": [{"name": "Python", "skill_type": "programming_language"}],
    "categories": [{
      "main_type": "Software",
      "sub_type": "Backend",
      "taxonomy_version": 1
    }],
    "location_ids": [],
    "skill_ids": [],
    "category_ids": []
  }'

curl http://127.0.0.1:8000/api/v1/jobs/<job_id>
```

Successful create and detail responses contain `job_id`, title, company,
locations, skills, grouped category, employment and seniority values,
description, requirements, source metadata, posted date, and salary fields.
The exact JSON schema and example are available in Swagger at `/docs`.

`GET /api/v1/jobs` supports text, company, location, skill, category,
employment, salary, sort, direction, and pagination parameters. Unknown IDs
return `404`, inconsistent category groups return `400`, invalid input returns
`422`, duplicates return `409`, and an unconfigured write service returns
`503`.

The normal-load regression test exercises a 100-row page with a two-second
local/CI budget and a fixed maximum of six `SELECT` statements. Filter indexes
live only in `app/sql/be19_job_details_migration.sql`, matching the project's
migration-owned schema policy.

The Silver sync currently maps the complete scraped advertisement into
`raw_description`; it does not extract a separate requirements section. The
`requirements` column is therefore populated for API-created records and stays
`null` for scraped records until the ingestion pipeline produces that field.
