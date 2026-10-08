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

## How It Works

```
Public ATS APIs ──► Scrapers ──► MinIO (bronze) ──► Cleaning + LLM (silver) ──► dbt (gold)
                                                                                    │
                                          Next.js frontend ◄── FastAPI ◄── PostgreSQL
```

| Layer | Tools |
| --- | --- |
| Ingest | Python, Greenhouse / Lever / Ashby / SmartRecruiters APIs |
| Storage | MinIO (Parquet), PostgreSQL, Supabase mirror |
| Processing | dbt, Groq LLM |
| API | FastAPI |
| Web | Next.js, React, TypeScript, Tailwind CSS |
| Ops | Docker Compose, GitHub Actions, Vercel |

## Quick Start

```bash
cp .env.sample .env        # fill in the required values
docker compose up --build  # frontend on :3000, API on :8000
```

For local development without Docker, see the [Frontend](#frontend), [Backend](#backend) and [Scrapers](#scrapers) sections.

## Table of Contents

- [Highlights](#highlights)
- [How It Works](#how-it-works)
- [Quick Start](#quick-start)
- [Problem](#problem)
- [Architecture](#architecture)
  - [Project Structure](#project-structure)
- [Frontend](#frontend)
- [Backend](#backend)
- [Scrapers](#scrapers)
- [Support](#support)

## Problem

> **One place to find, search and analyse autonomous vehicle job ads.**

### Overview

Autonomous vehicle (AV) jobs are spread across many separate employer career pages, and there is no single place to see what the industry is hiring for. This project solves that by:

- **Consolidating** AV job ads from multiple employers into one structured, searchable platform
- **Cutting fragmented searching** so users don't visit dozens of career pages by hand
- **Analysing skill demand** (skills, tools, qualifications) over time, as evidence for curriculum planning
- **Including adjacent technical roles**, not only titles that mention autonomous vehicles
- **Keeping traceability** with original source links for validation

## Architecture

> **Scrapers archive raw ATS payloads, a pipeline cleans and classifies them, and the API and frontend serve the result.**

![Main Architecture Diagram](./media/AV_mainarchitecture.drawio.svg)

### Project Structure

```
Autonomous_Vehicle_Job_Profiles_Group3/
├── api/                           # Vercel entrypoint
├── backend/                       # FastAPI service
│   ├── app/
│   │   ├── config/  core/  dependencies/  enums/  middleware/
│   │   ├── models/  schemas/  routers/  services/
│   │   ├── sql/                   # migrations / rollbacks
│   │   └── utils/
│   ├── scripts/                   # one-off scripts (e.g. backfills)
│   ├── evidence/
│   └── tests/ (unit_test/, integration_test/)
├── frontend/                      # Next.js + TypeScript + Tailwind
│   ├── app/                       # routes: account, companies, favorites,
│   │                              #   forgot-password, jobs, login, search,
│   │                              #   signup, trends
│   ├── components/ (ui/)
│   ├── lib/ (services/)
│   └── styles/  public/
├── scrapers/                      # Data pipeline (bronze → silver → gold)
│   ├── scraper_main.py            # fetch raw ATS payloads
│   ├── pipeline_main.py           # clean + classify
│   ├── config/  prompts/  script/  utils/
│   ├── models/ (bronze/, silver/)
│   ├── service/
│   │   ├── fetch/  bronze_storage/  silver_cleaning/
│   │   └── llm/    ml/
│   ├── dbt/ (macros/, models/)    # gold layer
│   ├── data/ (regression/, sample_data/, snapshots/)
│   ├── docs/
│   └── tests/ (unit_test/, integration_test/)
├── notebooks/                     # classifier experiments
├── document/                      # erd, gold-trend-mart, investigation,
│                                  #   plan, report, meeting notes
├── media/                         # README diagrams
├── .github/ (scripts/, workflows/)
├── docker-compose.yaml
└── vercel.json
```

## Frontend

> **Next.js web app for searching jobs and viewing skill trends.**

### Overview

Frontend application for Autonomous Vehicle Job Profiles (Next.js, React, TypeScript, Tailwind CSS).

### Technology

- Next.js
- React
- TypeScript
- Tailwind CSS
- ESLint
- Prettier

### Requirements

- Node.js 20.9 or later
- npm

### Installation

From the repository root:

```bash
cd frontend
npm install
```

### Environment variables

Copy `.env.example` to `.env.local`.

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Run locally

```bash
npm run dev
```

Open the following pages:

- http://localhost:3000
- http://localhost:3000/search

### Code checks

```bash
npm run format
npm run lint
npm run build
```

### End-to-end tests

Playwright drives a real browser through Find Jobs (keyword, country and
salary filters, pagination, empty and error states), the job detail page and
Market Trends. The API is mocked in the browser (`frontend/e2e/mock-api.ts`),
so no backend or database needs to be running.

```bash
npx playwright install chromium   # once, downloads the test browser
npm run test:e2e
```

The tests start their own dev server on port `3100`. They also run in the
frontend CI workflow on every pull request.

### Project structure

```text
app/              Next.js routes and pages
components/       Reusable React components
lib/services/     API configuration and service functions
styles/           Shared styles and documentation
public/           Static assets
```

## Backend

> **FastAPI service backed by PostgreSQL.**

### Overview

FastAPI API for autonomous vehicle job profiles.

### Requirements

- Python 3.10+
- PostgreSQL 14+ (local install)
- Packages in `backend/requirements.txt`

### PostgreSQL setup

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

**Optional: Docker instead of a local install**

```bash
docker run -d --name autojob-pg \
  -e POSTGRES_USER=team3 \
  -e POSTGRES_PASSWORD='<password>' \
  -e POSTGRES_DB=autojobdatabase \
  -p 5433:5432 \
  postgres:14
```

Then use port `5433` in `.env`. Later starts: `docker start autojob-pg`.

### Python environment

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
```

Use the same password you set when creating the Postgres user. If you used the Docker option above, use port `5433` instead.

Keep `SEED_ON_STARTUP=false` (see `backend/.env.sample`): `true` reseeds companies on *every* API start via `app/sql/seed_companies.sql`, which opens with `TRUNCATE TABLE company CASCADE` - that cascades through the FK graph and wipes every jobposting (Silver-synced categories, skills, and salary data included) down to the 12 hardcoded demo postings. Only set it `true` for a genuine from-scratch reseed on a database you don't mind emptying.

Backend CI starts an ephemeral Postgres service with `POSTGRES_HOST_AUTH_METHOD=trust` (no password). That is for GitHub Actions only — local Postgres should still use a password in `.env`.

### Run the API

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

### Companies API (testing)

**List companies**

```bash
curl http://127.0.0.1:8000/api/v1/companies
```

**Get company by id**

Use a `company_id` from the list response (or from the create response below):

```bash
curl http://127.0.0.1:8000/api/v1/companies/<company_id>
```

A new database with `SEED_ON_STARTUP=false` has no companies, so the list is
`[]` and any id returns `404` until you create one. The demo id
`11111111-1111-1111-1111-111111111035` only exists after seeding.

**Create a company**

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

When `SEED_ON_STARTUP=true`, created rows are replaced on restart because startup reseeds from the SQL file.

### Supabase mirror (optional)

Mirrors the backend's public schema - `company`, `jobposting`, `category`,
`skill`, `location`, and their join tables, **never `user_account`** - to a
hosted Supabase Postgres instance, so Supabase's auto-generated Data API can
serve it read-only. Off by default.

Set `SUPABASE_DATABASE_URL` in `.env` (see `backend/.env.sample` for the
connection-pooler string format) and it runs automatically after every
successful `sync_silver`/`import_categories`/`import_skills`/`import_salary`.
If the mirror fails, that command exits with status 1 (the local write has
already committed). To run it manually instead:

```bash
python -m scripts.sync_to_supabase
```

Each run is a full `pg_dump`/`pg_restore --clean` of those tables (not an
incremental sync), followed by `GRANT SELECT` on them for Supabase's
`anon`/`authenticated` roles. Leave `SUPABASE_DATABASE_URL` unset to disable
mirroring entirely.

## Scrapers

> **Fetches public ATS job payloads and archives them as Parquet in MinIO.**

### Overview

The scraper fetches public ATS job payloads (Greenhouse, Lever, Ashby,
SmartRecruiters) for every **enabled** API company in
`scrapers/data/list_companies.yaml` and archives the raw JSON as Parquet in
MinIO.

It only reads public job advertisements. It does not submit applications or
collect applicant information.

Run all scraper commands from the **repository root**. YAML paths and
`load_dotenv()` are relative to the current working directory.

### Job posting handling flow

![Job posting handling flow](./media/jobposting_handling.drawio.svg)

Each scraped posting fans out into three independent branches instead of
passing through one long chain:

| Branch | Steps | Output |
|---|---|---|
| Salary | Salary API + HTML extraction | Silver layer (backend ERD) |
| Classification | Regex pre-filter → few-shot classifier → hand-off of AV jobs → LLM + regex category definition | Silver layer (backend ERD) |
| Skills | Regex skill extraction | Extracted skills → star schema (gold layer) |

Why this design:

- **Cheap, deterministic steps first.** The regex pre-filter and few-shot
  classifier drop clearly non-AV roles before the LLM sees them, so only the
  hand-off set pays for LLM calls (see
  [Pre-filter jobs before LLM classification](#pre-filter-jobs-before-llm-classification)).
- **LLM and regex together for categories.** The LLM handles ambiguous titles;
  regex rules keep the category taxonomy consistent and auditable.
- **Independent branches.** Salary, classification and skills do not depend on
  each other, so one failing (for example an LLM provider outage) does not block
  the others, and each can be re-run or tuned on its own.
- **Skills use regex, not the LLM.** Skill matching is a fixed vocabulary
  lookup, which is repeatable and free to re-run over the whole bronze history.

### Requirements

- Python 3.10+
- Docker (for a local MinIO server)
- Packages in `scrapers/requirements.txt` (runtime; includes
  `sentence-transformers` / torch for the default embedding classifier)
- `scrapers/requirements-test.txt` for pytest (includes runtime)

```bash
python3 -m pip install -r scrapers/requirements.txt
# or, for tests:
python3 -m pip install -r scrapers/requirements-test.txt
```

### Initialize MinIO

The scraper writes bronze Parquet objects to MinIO. Start a local server, then
create a `.env` file at the **repository root** so credentials match.

**1. Start MinIO**

```bash
docker run -d --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  quay.io/minio/minio server /data --console-address ":9001"
```

- API: `http://localhost:9000`
- Console: `http://localhost:9001`

Log in to the console with `minioadmin` / `minioadmin`.

If MinIO is already running on this machine (for example via systemd), skip
Docker and set the `.env` values below to that server's endpoint and root
credentials.

**2. Configure environment variables**

Create `.env` in the repository root (this file is gitignored):

```bash
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
MINIO_JOBS_BUCKET=scraped-jobs
```

`MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` must match MinIO's root user and
password. `MINIO_SECURE=false` is required for local HTTP.

After archiving, the scraper loads the payloads into Postgres (`bronze` schema)
and builds the dbt models, so it also needs the database settings. Add them to
the same `.env` (see `scrapers/.env.sample`); without a password the archive
step still succeeds but the Postgres step fails with `no password supplied`:

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=autojobdatabase
POSTGRES_USER=team3
POSTGRES_PASSWORD=<password>
```

AutoBrains is read through Comeet's API, which needs a token. Set
`COMEET_TOKEN` in `.env` as well, or that company fails with
`unset environment variable for params.token` and the others still run.

The scraper creates the bucket on first archive if it does not already exist.
You do not need to create `scraped-jobs` by hand.

Defaults in `scrapers/config/minio.py` are the same as the values above, so a
local Docker MinIO with `minioadmin` works even without a `.env` file.

### Run the scraper

From the repository root:

```bash
python3 -m scrapers.scraper_main
```

Smoke-test a single company (use the `key` field from
`list_companies.yaml`):

```bash
python3 -m scrapers.scraper_main --company stack_av --max-jobs 10
```

| Flag | Default | Meaning |
|---|---|---|
| `--company` | all enabled API companies | Run one company by YAML `key` |
| `--max-jobs` | `100` | Maximum jobs kept from each company response |
| `--timeout` | `30` | HTTP timeout in seconds |

Companies with `enabled: false`, or an ATS that is not an API source, are
skipped. Raw payloads are stored as:

```text
{bucket}/api/{company_slug}/{company_slug}_{YYYY-MM-DD_HH-MM-SS}.parquet
```

Browse them in the MinIO console at
[http://localhost:9001](http://localhost:9001) under the `scraped-jobs` bucket.

![MinIO console showing bronze Parquet objects](./media/minio_bronze_sample.png)

### Pre-filter jobs before LLM classification

Run the deterministic pre-filter on a CSV, JSON array, or JSON Lines export of
`bronze.job_postings` before sending rows to an LLM:

```bash
python3 -m scrapers.utils.job_prefilter \
  --input scrapers/data/sample_data/job_postings_202609011519.csv \
  --output-dir data/job_prefilter
```

The command creates four outputs:

- `llm_candidates.jsonl`: rows allowed to proceed to classification
- `excluded_jobs.jsonl`: complete excluded rows, filtering decision, and audit category
- `filter_metrics.json`: before, after, excluded, and reduction counts per company
- `filter_decisions.csv`: compact, review-friendly result for every input job

A committed example generated from 100 Silver-layer rows is available at
`scrapers/data/sample_data/job_prefilter_decisions_sample.csv`.

Rules live in `scrapers/config/job_prefilter.yaml`. Set
`AV_JOB_PREFILTER_CONFIG` or pass `--config` to use an external YAML file. The
safe default excludes only explicit corporate/support titles and sends unknown
roles to the LLM for review. Set `exclude_below_threshold: true` only after the
positive keyword rules have been validated against representative data.

Notebook code can use the same gate directly:

```python
from scrapers.service.llm import JobPrefilter

prefilter = JobPrefilter.from_config()
filter_result = prefilter.filter(jobs_df.to_dict(orient="records"))
filter_result.write_outputs(PROJECT_ROOT / "data" / "job_prefilter")
llm_jobs_df = pd.DataFrame(filter_result.included).drop(
    columns=["_prefilter"], errors="ignore"
)
```

The existing notebook Groq model and API-key configuration remain unchanged.
Only `llm_jobs_df` should be passed to the model. The LLM adapter can be changed
later without changing or losing the pre-filter audit trail.

### How the scraped data shapes the design

<details>
<summary>From messy source payloads to the bronze / silver / gold layers</summary>

| What the scraped data looks like | Design decision |
|---|---|
| 38 enabled companies on different sources: 30 ATS APIs, 7 HTML pages and 1 XML feed, each with its own JSON or markup | Store every raw payload untouched in MinIO and `bronze.raw_responses` (JSONB), then parse it with one dbt model per source |
| Fields are inconsistent or missing across sources (salary, location, description) | Keep optional fields nullable and normalise only in the silver layer, so raw evidence is never lost |
| Some list pages have no description | `RawFetch` also fetches each job's detail page and embeds it in the bronze payload |
| The row id is a volatile `row_number()` between runs | Use `job_id`, the ATS-native posting id (falling back to the URL, then a content hash), for joins and cross-run comparison |
| Descriptions are free text with no structured skills or category | Run regex skill extraction on the cleaned text, and use the pre-filter, classifier and LLM for AV relevance and category |
| Salary appears in structured API fields for some sources and only in text for others | Run salary as its own branch, so it can be re-run or tuned independently |

Because the bronze layer keeps the raw responses, any parser, classifier or skill list can be changed and re-run over the whole history without scraping again.

</details>

### Why this classifier

<details>
<summary>Model comparison: frozen embedding vs SetFit</summary>

Both were tested on the same Groq-labelled seed set (202 AV / 197 non-AV, stratified 80/20 split).

![Train vs test accuracy: frozen MiniLM embedding + logistic regression vs SetFit](media/model_comparison.png)

- **Frozen MiniLM + logistic regression** trains and tests close together (about 80% train, 77% test), so it generalises steadily.
- **SetFit** reaches 100% train accuracy almost immediately, while test accuracy peaks near 84% and then falls to 78-80%. It overfits on a seed set this small.

</details>

### Why not a full deep learning model

<details>
<summary>Project scale and why we went few-shot</summary>

Training a deep model end to end needs thousands of labelled examples. Our scale is much smaller:

| Factor | Our project |
|---|---|
| Labelled data | 399 Groq-labelled postings (319 train / 80 test) |
| Sources | 38 enabled companies |
| Postings | ~5,400 scraped; 1,229 AV postings shown on the platform |
| Labelling cost | LLM labels cost money per call, so labelling thousands of postings was not practical |

- **Too few labels for end-to-end training.** A large network fitted on about 400 examples memorises them. SetFit already shows this: 100% train accuracy but a test curve that peaks and then drops.
- **Few-shot reuses a pretrained encoder.** MiniLM already understands language, so a small classifier head (or a short contrastive fine-tune) is enough to separate AV from non-AV roles.
- **The classifier is a cheap first gate.** It drops clearly non-AV roles so the LLM only sees the hand-off set, which keeps LLM cost down as more companies are added.
- **Easy to re-run.** A frozen embedding plus logistic regression fits in seconds, so the model can be retrained whenever the seed set grows.

</details>

### Run tests

From the repository root:

```bash
python3 -m pytest scrapers/tests/unit_test scrapers/tests/integration_test -v
```

## Support

If you find this project useful, please consider giving it a ⭐ on [GitHub](https://github.com/husthunterpy01/Autonomous_Vehicle_Job_Profiles_Group3). Every star is a free donation that helps the project get noticed and keeps us motivated.
