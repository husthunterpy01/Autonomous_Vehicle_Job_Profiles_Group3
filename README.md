# CITS5206 Capstone Project

Capstone project for UWA IT course.

The proposed architecture of the system:

![Capstone Architecture Diagram](./capstone_flow.drawio.svg)

## Frontend

Frontend application for Autonomous Vehicle Job Profiles (Next.js, React, TypeScript, Tailwind CSS).

<details>
<summary>Technology</summary>

- Next.js
- React
- TypeScript
- Tailwind CSS
- ESLint
- Prettier

</details>

<details>
<summary>Requirements</summary>

- Node.js 20.9 or later
- npm

</details>

<details>
<summary>Installation</summary>

From the repository root:

```bash
cd frontend
npm install
```

</details>

<details>
<summary>Environment variables</summary>

Copy `.env.example` to `.env.local`.

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

</details>

<details>
<summary>Run locally</summary>

```bash
npm run dev
```

Open the following pages:

- http://localhost:3000
- http://localhost:3000/search

</details>

<details>
<summary>Code checks</summary>

```bash
npm run format
npm run lint
npm run build
```

</details>

<details>
<summary>Project structure</summary>

```text
app/              Next.js routes and pages
components/       Reusable React components
lib/services/     API configuration and service functions
styles/           Shared styles and documentation
public/           Static assets
```

</details>

## Backend

FastAPI API for autonomous vehicle job profiles.

<details>
<summary>Requirements</summary>

- Python 3.10+
- PostgreSQL 14+ (local install)
- Packages in `backend/requirements.txt`

</details>

<details>
<summary>PostgreSQL setup</summary>

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

</details>

<details>
<summary>Python environment</summary>

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
```

Use the same password you set when creating the Postgres user. If you used the Docker option above, use port `5433` instead.

`SEED_ON_STARTUP=true` reseeds companies on every API start (local/dev). Leave it unset or `false` outside local development so production data is not truncated.

Backend CI starts an ephemeral Postgres service with `POSTGRES_HOST_AUTH_METHOD=trust` (no password). That is for GitHub Actions only — local Postgres should still use a password in `.env`.

</details>

<details>
<summary>Run the API</summary>

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

</details>

<details>
<summary>Companies API (testing)</summary>

**List companies**

```bash
curl http://127.0.0.1:8000/api/v1/companies
```

**Get company by id**

```bash
curl http://127.0.0.1:8000/api/v1/companies/11111111-1111-1111-1111-111111111035
```

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

</details>

## Scrapers

The scraper fetches public ATS job payloads (Greenhouse, Lever, Ashby,
SmartRecruiters) for every **enabled** API company in
`scrapers/data/list_companies.yaml` and archives the raw JSON as Parquet in
MinIO.

It only reads public job advertisements. It does not submit applications or
collect applicant information.

Run all scraper commands from the **repository root**. YAML paths and
`load_dotenv()` are relative to the current working directory.

<details>
<summary>Requirements</summary>

- Python 3.10+
- Docker (for a local MinIO server)
- Packages in `scrapers/requirements-test.txt`

```bash
python3 -m pip install -r scrapers/requirements-test.txt
```

</details>

<details>
<summary>Initialize MinIO</summary>

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

The scraper creates the bucket on first archive if it does not already exist.
You do not need to create `scraped-jobs` by hand.

Defaults in `scrapers/config/minio.py` are the same as the values above, so a
local Docker MinIO with `minioadmin` works even without a `.env` file.

</details>

<details>
<summary>Run the scraper</summary>

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

</details>

<details>
<summary>Pre-filter jobs before LLM classification</summary>

Run the deterministic pre-filter on a CSV, JSON array, or JSON Lines export of
`bronze.job_postings` before sending rows to an LLM:

```bash
python3 -m scrapers.job_prefilter \
  --input scrapers/data/sample_data/job_postings_202609011519.csv \
  --output-dir data/job_prefilter
```

The command creates three outputs:

- `llm_candidates.jsonl`: rows allowed to proceed to classification
- `excluded_jobs.jsonl`: complete excluded rows, filtering decision, and audit category
- `filter_metrics.json`: before, after, excluded, and reduction counts per company

Rules live in `notebooks/config/job_prefilter.yaml`. Set
`AV_JOB_PREFILTER_CONFIG` or pass `--config` to use an external YAML file. The
safe default excludes only explicit corporate/support titles and sends unknown
roles to the LLM for review. Set `exclude_below_threshold: true` only after the
positive keyword rules have been validated against representative data.

Notebook code can use the same gate directly:

```python
from scrapers.service.job_prefilter import JobPrefilter

prefilter = JobPrefilter.from_config()
filter_result = prefilter.filter(jobs_df.to_dict(orient="records"))
filter_result.write_outputs(PROJECT_ROOT / "data" / "job_prefilter")
llm_jobs_df = pd.DataFrame(filter_result.included)
```

The existing notebook Groq model and API-key configuration remain unchanged.
Only `llm_jobs_df` should be passed to the model. The LLM adapter can be changed
later without changing or losing the pre-filter audit trail.

</details>

<details>
<summary>Run tests</summary>

From the repository root:

```bash
python3 -m pytest scrapers/tests/unit_test scrapers/tests/integration_test -v
```

</details>
