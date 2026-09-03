# Job scrapers

Setup, MinIO, and run instructions live in the
[Scrapers section of the root README](../README.md#scrapers).

# Silver cleaning

The first Silver step creates a cleaned, flat dbt model from
`bronze.job_postings`. Run it after the Bronze dbt model has completed:

```bash
python -m scrapers.service.silver_cleaning.silver_ingest
```

The Python command is a thin dbt runner, so transformation execution and logging
are handled by dbt. The model keeps the Bronze `id`, ignores query-only columns such as `rn`, removes
records without a title or description, strips HTML from descriptions,
normalizes timestamps, employment types and multi-location values, and
deduplicates by source job ID, job URL, then normalized fallback fields. It builds
`silver.cleaned_job_postings` on each successful run.

Skills extraction is exposed separately in `skills_extractor.py`, with its prompt
stored in `scrapers/prompts/skills_extraction.txt`. AV-domain
classification is intentionally excluded because it is owned by the separate
classification task.
