FROM python:3.10-slim

WORKDIR /app

# Build context is this directory (scrapers/), matching backend/frontend's
# per-service context in docker-compose.yaml - Docker only reads
# .dockerignore from the context root, so it must be built as
# `docker build -f scrapers/Dockerfile scrapers/`, never from the repo root
# (that would skip .dockerignore entirely, pulling scrapers/.env's DB
# credentials into the image, and send the whole repo as build context).
# Paths below are relative to scrapers/, not the repo root.
COPY requirements.txt ./scrapers/requirements.txt
RUN pip install --no-cache-dir -r scrapers/requirements.txt

# Code lands under /app/scrapers so it's importable as the `scrapers`
# package and scrapers/config/dbt.py's "./scrapers/dbt" relative path still
# resolves - both assume /app (this WORKDIR) stands in for the repo root at
# runtime, same as every entrypoint's `python -m scrapers.<module>` docs.
COPY . ./scrapers

RUN useradd --create-home appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
USER appuser

CMD ["python3", "-m", "scrapers.pipeline_main"]
