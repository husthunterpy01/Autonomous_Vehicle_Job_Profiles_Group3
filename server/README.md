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
cd server
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
```

Use the same password you set when creating the Postgres user. If you used the Docker option above, use port `5433` instead.

### CI note

GitHub Actions reads the Postgres password from the repository secret `POSTGRES_PASSWORD` (Settings → Secrets and variables → Actions). Set that secret before relying on backend CI.

## Run

From the `server/` directory (Postgres must already be running):

```bash
python3 -m uvicorn app.main:app --reload
```

On startup the API:

1. Creates tables if they do not exist
2. Reseeds the company list from `app/sql/seed_companies.sql` (runs on every start)

The API listens on [http://127.0.0.1:8000](http://127.0.0.1:8000).

| URL | Description |
|---|---|
| http://127.0.0.1:8000/docs | Swagger UI |
| http://127.0.0.1:8000/redoc | ReDoc |
| http://127.0.0.1:8000/health | Health check |
| http://127.0.0.1:8000/api/v1/companies | Companies API |

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

Note: created rows are replaced when the server restarts, because startup reseeds from the SQL file.
