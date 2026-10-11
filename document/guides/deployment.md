# Deployment

How the platform is run and released: Docker Compose, Vercel, GitHub Pages, the database and its migrations. For the project overview and local development, see the [main README](../../README.md). For the scrapers, see [scrapers-setup.md](./scrapers-setup.md).

## Contents

- [Where things run](#where-things-run)
- [Environment variables](#environment-variables)
- [Docker Compose](#docker-compose)
- [Vercel (frontend and API)](#vercel-frontend-and-api)
- [GitHub Pages (frontend only)](#github-pages-frontend-only)
- [Database and migrations](#database-and-migrations)
- [Supabase mirror](#supabase-mirror)
- [Release checklist](#release-checklist)
- [Security checklist](#security-checklist)
- [CI/CD workflows](#cicd-workflows)
- [Troubleshooting](#troubleshooting)

## Where things run

| Target | What it serves | How it is deployed |
|---|---|---|
| **Vercel** | the Next.js frontend and the FastAPI backend on one domain | `cd-vercel.yml`, on every push to `main` that touches the app |
| **GitHub Pages** | the static frontend only | `cd-frontend.yml`, on every push to `main` |
| **Docker Compose** | frontend and backend on your own machine or server | `docker compose up --build` |
| **Supabase (Postgres)** | the database used by the backend | schema changes are applied by hand (see [Database and migrations](#database-and-migrations)) |

## Environment variables

Each place that runs the backend needs its own settings. The full list with comments is in `backend/.env.sample`; these are the ones that matter for a deployment.

| Variable | Needed | Notes |
|---|---|---|
| `DATABASE_URL` | yes | Postgres connection string. For Supabase use the **pooler** string and add `?sslmode=require`. |
| `JWT_SECRET_KEY` | yes | Required outside development. Generate with `openssl rand -hex 32`; never reuse a memorable value. |
| `ENVIRONMENT` | yes | Set to `production`. |
| `AUTH_COOKIE_SECURE` | yes on HTTPS | Defaults to `false`. Set `true` in production so the session cookie is only sent over HTTPS. |
| `SEED_ON_STARTUP` | keep `false` | `true` runs `TRUNCATE TABLE company CASCADE` on every start and wipes the job data. Never set it against a shared or hosted database. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_STARTTLS` | for password-reset emails | Without `SMTP_HOST` the API starts, but reset emails cannot be delivered. |
| `PASSWORD_RESET_FRONTEND_URL` | for password-reset emails | The public address of the reset page. |
| `JOB_WRITE_API_KEY` | for `POST /api/v1/jobs` | Sent by callers in the `X-Job-Write-Key` header. |
| `GOLD_DATABASE_URL` | optional | A read-only connection to the gold trend database. Unset, the Market Trends endpoint returns 503 and the page shows its "not configured" message. |
| `AUTH_LOGIN_MAX_ATTEMPTS`, `AUTH_LOGIN_WINDOW_SECONDS` | optional | Defaults 5 attempts per 300 seconds. Also used for wrong current-password attempts when editing an account. |
| `DATABASE_CONNECT_TIMEOUT` | optional | Seconds to wait for Postgres before failing (default 10). |
| `NEXT_PUBLIC_API_URL` | frontend, at **build** time | The API's origin. It defaults to `http://localhost:8000`, which only works on your own machine, so set it for every deployed build. |

The login rate limiter keeps its counters in memory, so on serverless hosting the limit applies per instance, not globally.

## Docker Compose

`docker-compose.yaml` builds and runs the frontend (port 3000) and the backend (port 8000).

```bash
cp .env.sample .env     # then fill in the values below
docker compose up --build
```

Older installs use `docker-compose` (with a hyphen) instead of `docker compose`.

The root `.env` is read by Compose on the host. It is separate from `backend/.env` and `scrapers/.env`, and the Compose backend does not read `backend/.env`.

| Variable | Notes |
|---|---|
| `JWT_SECRET_KEY` | Required. |
| `SUPABASE_DATABASE_URL` | Required. Passed to the backend as its `DATABASE_URL`. |
| `GOLD_DATABASE_URL` | Optional. |

**Important:** the Compose backend uses `SUPABASE_DATABASE_URL` as its database. Running Compose locally therefore talks to the **hosted** database, and anyone who signs up or edits an account through it changes real data. To use a local database instead, run the backend directly (see [Run it without Docker](../../README.md#run-it-without-docker)) or point `SUPABASE_DATABASE_URL` at a throwaway Postgres.

The frontend image is built with `NEXT_PUBLIC_API_URL=http://localhost:8000`, so it expects the API on the same machine.

## Vercel (frontend and API)

`vercel.json` builds two things and routes them on one domain:

- `frontend/` with `@vercel/next`
- `api/index.py` with `@vercel/python`. It puts `backend/` on the Python path and exposes the FastAPI `app`. The routes `/api/*`, `/health`, `/docs`, `/redoc` and `/openapi.json` go to it.

**How it deploys.** `.github/workflows/cd-vercel.yml` runs on every push to `main` that changes `frontend/`, `backend/app/`, `backend/requirements.txt`, `api/`, `vercel.json`, `.vercelignore` or the workflow. It pulls the project settings, builds with the Vercel CLI, strips a few unused files, then deploys the prebuilt output. Vercel's own Git integration is turned off (`"deploymentEnabled": false`).

**One-time setup.** Add three repository secrets in GitHub (Settings, Secrets and variables, Actions): `VERCEL_TOKEN`, `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID`. The org and project ids are in `.vercel/project.json` after `vercel link`. The workflow stops with a clear error if one is missing.

**Project settings.** Set the [environment variables](#environment-variables) above in the Vercel project (Settings, Environment Variables), including `NEXT_PUBLIC_API_URL`, which is baked in when the frontend is built.

**Keep `api/requirements.txt` in step.** Vercel cannot read pip's `-r` include, so `api/requirements.txt` is a hand-maintained copy of `backend/requirements.txt` without `pytest`. The backend CI fails if they differ (`.github/scripts/check_api_requirements.py`). When you add a backend dependency, add it in both files.

**Check a deployment:**

```bash
curl https://<your-domain>/health
# {"status":"ok"}

curl -X POST https://<your-domain>/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier":"nobody-here","password":"x"}'
# {"detail":"Incorrect username/email or password"}   (401, not 500)
```

A `500` from the login call means the API cannot read the user table, almost always because a migration was not applied (see below).

## GitHub Pages (frontend only)

`cd-frontend.yml` builds the frontend as a static export (`output: "export"`) with `GITHUB_PAGES=true`, which serves it under `/Autonomous_Vehicle_Job_Profiles_Group3`, and publishes `frontend/out`.

Pages hosts no API. As configured, the workflow does not set `NEXT_PUBLIC_API_URL`, so the build points at `http://localhost:8000` and pages that need data cannot load it. Signing in would also need the API to allow that origin (`CORS_ORIGINS`) and a cookie that works across sites. Use Vercel for the working platform; treat Pages as a static preview unless you set an API address in that workflow.

## Database and migrations

The backend creates **missing tables** on startup, but it never changes a table that already exists. A new column in the code does not appear in a hosted database by itself. The SQL files in `backend/app/sql/` add them, and they are applied **by hand**.

The files are named by the feature that introduced them. Apply the ones a release adds, in numeric order, and read each file's header for what it needs first.

| File | Adds |
|---|---|
| `be9_migration.sql` | the base backend tables (apply first on an existing database) |
| `be10_salary_migration.sql` | salary columns |
| `be11_favorites_migration.sql` | `favorite_job` and `favorite_company` |
| `be13_salary_constraints_migration.sql` | salary check constraints (also needed on a fresh database) |
| `be15_drop_job_location_migration.sql` | removes the old `job_location` text column |
| `be18_user_profile_migration.sql` | `user_account.phone` and `address` |
| `be19_job_details_migration.sql` | job detail columns |
| `be20_password_reset_migration.sql` | `user_account.token_version` and `password_reset_token` |
| `be21_location_country_migration.sql`, `be31_location_country_column_migration.sql` | location country (BE-31 replaces the BE-21 table with a column) |
| `clean_location_labels_migration.sql`, `company_description_migration.sql` | location label cleanup, company description |

`be10`, `be13`, `be19`, `be21`, `be31` and `company_description` have matching `*_rollback.sql` files.

Apply a file with `psql`, stopping at the first error:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/app/sql/be18_user_profile_migration.sql
```

or paste it into the Supabase SQL editor. Back the database up first. `be18` and `be20` are written to be repeatable and non-destructive; check the header of any other file before running it twice.

**Why this matters.** When BE-18 shipped, its migration was not run on the hosted database. Every query on `user_account` then failed because the code selects `phone` and `address`, and nobody could sign in or sign up (the login endpoint returned 500). Adding the two columns fixed it immediately.

To check a table against what the code expects:

```sql
select column_name from information_schema.columns
where table_schema = 'public' and table_name = 'user_account'
order by ordinal_position;
-- expect: user_id, email, username, full_name, password_hash, is_active,
--         created_at, token_version, phone, address
```

## Supabase mirror

The mirror copies the backend's public tables (`company`, `jobposting`, `category`, `skill`, `location` and their join tables, never `user_account`) from a local or staging database to a hosted Supabase Postgres, so the Data API can serve them read-only. It is off by default.

Set `SUPABASE_DATABASE_URL` (the pooler string, see `backend/.env.sample`) and it runs automatically after every successful `sync_silver`, `import_categories`, `import_skills` or `import_salary`. If the mirror fails, that command exits with status 1; the local write has already been saved. To run it by hand:

```bash
cd backend
python -m scripts.sync_to_supabase
```

Each run is a full `pg_dump` and `pg_restore --clean` of those tables, not an incremental sync, followed by `GRANT SELECT` for Supabase's `anon` and `authenticated` roles. Leave `SUPABASE_DATABASE_URL` unset to turn it off.

Because the mirror replaces the hosted tables, run it from a database that has every migration applied; otherwise it overwrites newer data with older data.

## Release checklist

1. CI is green on the pull request (backend, frontend, scrapers if touched, and the Vercel build check).
2. List any new files in `backend/app/sql/` the change adds.
3. **Before merging**, back up the hosted database and apply those migrations, or the new code will fail against the old schema.
4. If `backend/requirements.txt` changed, `api/requirements.txt` matches (the backend CI checks this).
5. Merge to `main`. `cd-vercel.yml` and `cd-frontend.yml` deploy automatically.
6. Smoke-test with the two `curl` calls in [Vercel](#vercel-frontend-and-api), then open the site, search for jobs and sign in.

## Security checklist

- **Row Level Security is off.** At the last check (8 Oct 2026) Supabase reported RLS disabled on every table in `public`, including `user_account` (password hashes) and `password_reset_token`. Anyone holding the project's public anon key can read or change those rows through the Supabase API. Decide which tables the API should expose, enable RLS, and add policies; enabling RLS without policies blocks all access, so test first.
- Keep `AUTH_COOKIE_SECURE=true` on HTTPS and `SEED_ON_STARTUP=false` everywhere.
- Keep secrets (`JWT_SECRET_KEY`, database URLs, SMTP and Vercel tokens) in the host's secret store, never in the repository.
- Do not point a development or Compose environment at the production database unless you mean to change production data.

## CI/CD workflows

| Workflow | Runs on | What it does |
|---|---|---|
| `ci-backend.yml` | pull requests and pushes touching `backend/` | `api/requirements.txt` check, ruff, unit and integration tests against a Postgres service |
| `ci-frontend.yml` | pull requests | format check, lint, unit tests, Playwright end-to-end tests |
| `ci-scrapers.yml` | changes under `scrapers/` | scraper tests |
| `ci-vercel.yml` | pull requests touching the deployed app | Vercel build check |
| `cd-vercel.yml` | push to `main` | deploy to Vercel |
| `cd-frontend.yml` | push to `main` | deploy the static frontend to GitHub Pages |

## Troubleshooting

| What you see | Cause and fix |
|---|---|
| Sign-in or sign-up returns 500 | A migration is missing on the hosted database. Compare `user_account` with the check above and apply the missing `be*_migration.sql`. |
| The Compose backend never answers and its log stops at "Waiting for application startup" | The container cannot reach the database. Test from the container; if it has no outbound network, run `docker compose down` and `up` again so Docker recreates the project network. The backend now gives up after 10 seconds with a "timeout expired" error instead of hanging. |
| The frontend shows no data on a deployment | `NEXT_PUBLIC_API_URL` was not set at build time, so it points at `localhost:8000`. Set it and redeploy. |
| Vercel deploy stops with "Repository secret … is not set" | Add `VERCEL_TOKEN`, `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` in the repository secrets. |
| Backend CI fails on the requirements check | `api/requirements.txt` and `backend/requirements.txt` differ. Update both. |
