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
SEED_ON_STARTUP=true
JWT_SECRET_KEY=<generate-a-long-random-secret>
AUTH_COOKIE_SECURE=false
```

Use the same password you set when creating the Postgres user. If you used the Docker option above, use port `5433` instead.

`SEED_ON_STARTUP=true` reseeds companies on every API start (local/dev). Leave it unset or `false` outside local development so production data is not truncated.

Generate `JWT_SECRET_KEY` with a cryptographically secure random generator and
keep it outside source control. Set `AUTH_COOKIE_SECURE=true` when the frontend
and API are served over HTTPS. Any environment other than an explicitly named
`development` environment fails at startup when `JWT_SECRET_KEY` is missing.

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

## Authentication API

Passwords must contain at least 12 characters, including uppercase, lowercase,
a number, and a special character. Passwords are stored as Argon2 hashes. The
signed JWT contains only the user ID, token type, issued-at time, and expiry and
is returned in an HTTP-only `SameSite=Lax` cookie rather than response JSON.

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
