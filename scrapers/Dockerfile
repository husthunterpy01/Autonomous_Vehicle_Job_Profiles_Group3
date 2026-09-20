FROM python:3.10-slim

WORKDIR /app

COPY scrapers/requirements-test.txt ./scrapers/requirements-test.txt
RUN pip install --no-cache-dir -r scrapers/requirements-test.txt

COPY ./scrapers ./scrapers

RUN useradd --create-home appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
USER appuser

CMD ["python3", "-m", "scrapers.pipeline_main"]
