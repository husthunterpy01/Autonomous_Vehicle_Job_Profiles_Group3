# Autonomous Vehicle Job Profiles

> **What is the autonomous vehicle industry hiring for, and which skills should students learn next?**

CITS5206 Capstone Project (UWA), Group 3.

We collect public job ads from AV employers, clean and classify them with an LLM, and turn them into a searchable job board and skill-trend dashboard.

![AV Job Finder homepage](media/homepage.png)

![Top skills in demand over time](media/skill_trends.png)

*Market Trends page: monthly count of job postings that list each skill.*

## Highlights

- 🔎 **Search every AV job in one place**, with filters such as salary range and country
- 📈 **See skill demand over time**, including tools, languages and qualifications
- 🧠 **LLM-assisted classification** finds AV roles, including adjacent ones that never say "autonomous"
- 🔗 **Every job links back to its original posting** so results are easy to verify
- 🗄️ **Bronze → silver → gold pipeline** keeps raw payloads, cleaned data and analytics separate

## How it works

```
Public ATS APIs ──► Scrapers ──► MinIO (bronze) ──► Cleaning + LLM (silver) ──► dbt (gold)
                                                                                    │
                                          Next.js frontend ◄── FastAPI ◄── PostgreSQL
```

![Main architecture diagram](./media/AV_mainarchitecture.drawio.svg)

| Layer | Tools |
| --- | --- |
| Ingest | Python, Greenhouse / Lever / Ashby / SmartRecruiters APIs |
| Storage | MinIO (Parquet), PostgreSQL, Supabase mirror |
| Processing | dbt, Groq LLM |
| API | FastAPI |
| Web | Next.js, React, TypeScript, Tailwind CSS |
| Ops | Docker Compose, GitHub Actions, Vercel |

## Try it with the demo account

Use this account to look around without registering your own.

| | |
| --- | --- |
| **Username** | `demo.user` |
| **Email** | `demo.user@example.com` |
| **Password** | `Demo!Passw0rd2026` |

Sign in at `/login` with either the username or the email. The account is not created for you: make it once in the environment you are running, either on the **Sign up** page or with one command (the API must be running):

```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"demo.user@example.com","username":"demo.user","full_name":"Demo User","password":"Demo!Passw0rd2026"}'
```

`201` means it was created; `409` means it already exists, so just sign in.

Things to try once you are in: filter **Find Jobs** by country and salary, open a job and save it to your **Favorites**, look at **Market Trends**, and open **My Account** to edit the profile or change the password.

> On a shared deployment please do not change this account's password, so it keeps working for the next person.

## Quick start (Docker)

```bash
cp .env.sample .env        # fill in JWT_SECRET_KEY and SUPABASE_DATABASE_URL
docker compose up --build  # frontend on :3000, API on :8000
```

Then open [http://localhost:3000](http://localhost:3000). The API's interactive docs are at [http://localhost:8000/docs](http://localhost:8000/docs).

> **Heads up:** the Compose backend uses `SUPABASE_DATABASE_URL` as its database, so it works with the hosted data and anything you change (sign-ups, account edits) is real. To work against your own database, [run it without Docker](#run-it-without-docker). Details are in the [deployment guide](document/guides/DEPLOYMENT.md).

## Run it without Docker

You need **Python 3.10+**, **Node.js 20.9+** and a **PostgreSQL 14+** database.

**1. Database.** The quickest way is a throwaway container:

```bash
docker run -d --name autojob-pg \
  -e POSTGRES_USER=team3 -e POSTGRES_PASSWORD=change-me -e POSTGRES_DB=autojobdatabase \
  -p 5433:5432 postgres:14
```

(or install PostgreSQL locally and create a `team3` user and an `autojobdatabase` database).

**2. Backend.**

```bash
cd backend
pip install -r requirements.txt
cp .env.sample .env
```

In `backend/.env` set `DATABASE_URL=postgresql://team3:change-me@localhost:5433/autojobdatabase` (use port `5432` for a local install) and keep `ENVIRONMENT=development`. Then:

```bash
python3 -m uvicorn app.main:app --reload
```

The API runs on [http://localhost:8000](http://localhost:8000) (Swagger at `/docs`, health check at `/health`). It creates the tables on first start.

A new database has no jobs. To load a few demo companies and postings, set `SEED_ON_STARTUP=true` for one start **on a new, empty database only**, then set it back to `false`. The seed wipes the job tables, so never use it on a database that holds real data.

**3. Frontend.** In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local     # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Open [http://localhost:3000](http://localhost:3000), sign up (or create the [demo account](#try-it-with-the-demo-account)) and explore.

**Real job data** comes from the scrapers; see [Scrapers: environment setup](document/guides/SCRAPERS_SETUP.md).

## Tests and checks

| What | Command |
| --- | --- |
| Backend lint and tests | `cd backend && ruff check . && python3 -m pytest tests` |
| Frontend format, lint and unit tests | `cd frontend && npm run format:check && npm run lint && npm test` |
| Frontend end-to-end (Playwright, mocked API) | `cd frontend && npx playwright install chromium && npm run test:e2e` |
| Scrapers | `python3 -m pytest scrapers/tests/unit_test scrapers/tests/integration_test` |

All of them run in CI on every pull request. The end-to-end tests use a hand-written mock API, so they check the pages but not the contract with the real backend; see [document/frontend/E2E_TESTING.md](document/frontend/E2E_TESTING.md).

## Documentation

| Guide | What it covers |
| --- | --- |
| [Scrapers: environment setup](document/guides/SCRAPERS_SETUP.md) | MinIO, the scraper `.env`, running the scraper and the full pipeline, pre-filter, design notes |
| [Deployment](document/guides/DEPLOYMENT.md) | Docker Compose, Vercel, GitHub Pages, environment variables, database migrations, release and security checklists |
| [Backend README](document/backend/README.md) | Authentication API, endpoints, configuration |
| [Frontend README](document/frontend/README.md) | Pages, environment, code checks |
| [End-to-end tests](document/frontend/E2E_TESTING.md) | The Playwright suite, the mock API and its limits |
| [Silver sync](document/backend/SILVER_SYNC.md) | Loading classified jobs into the backend tables |
| [Pipeline README](document/scrapers/README.md) | Cleaning, classification and enrichment stages in detail |
| [Accessibility audit](document/report/accessibility_audit.md) | WCAG 2.1 AA findings and fixes |
| [Data quality check](document/report/data_quality_sample_check.md) | Spot check of the data against the source pages |

## Project structure

```
Autonomous_Vehicle_Job_Profiles_Group3/
├── backend/        FastAPI service (app/, tests/, scripts/, SQL migrations in app/sql/)
├── frontend/       Next.js + TypeScript + Tailwind (app/, components/, lib/, e2e/)
├── scrapers/       data pipeline: fetch, clean, classify (service/, dbt/, prompts/, tests/)
├── api/            Vercel entry point for the backend
├── document/       guides, reports, ERD, plans and meeting notes
├── notebooks/      classifier experiments
├── media/          images and diagrams used in the docs
├── .github/        CI/CD workflows
├── docker-compose.yaml
└── vercel.json
```

## Support

If you find this project useful, please consider giving it a ⭐ on [GitHub](https://github.com/husthunterpy01/Autonomous_Vehicle_Job_Profiles_Group3). Every star is a free donation that helps the project get noticed and keeps us motivated.
