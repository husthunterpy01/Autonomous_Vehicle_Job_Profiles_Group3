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

# AV classification and enrichment

These steps pick up after `silver.cleaned_job_postings` exists. Run them from
the **repository root**, in order:

**1. Export Silver rows to a flat file**

```bash
python3 -m scrapers.service.silver_cleaning.silver_export
```

Runs `SELECT * FROM silver.cleaned_job_postings` and writes it to
`data/silver_export.jsonl` (override with `--output <path>`). This is the
handoff point between the dbt-managed Silver table and the file-based stages
below.

**2. Pre-filter (deterministic, no LLM)** - see
[Pre-filter jobs before LLM classification](../README.md#scrapers) in the root
README for the full write-up.

```bash
python3 -m scrapers.utils.job_prefilter \
  --input data/silver_export.jsonl \
  --output-dir data/job_prefilter
```

Writes `llm_candidates.jsonl` (rows that need an LLM call) plus
`excluded_jobs.jsonl`, `filter_metrics.json`, and `filter_decisions.csv`.

**3. LLM AV-relevance classification**

```bash
python3 -m scrapers.utils.job_classifier \
  --input data/job_prefilter/llm_candidates.jsonl \
  --output-dir data/job_classification
```

Batches jobs (default 20/request) through Groq to screen for AV relevance
only - cheap, no category taxonomy in the prompt. Writes
`av_candidates.jsonl` (AV-relevant), `non_av_jobs.jsonl`, `relevance_failed_jobs.jsonl`,
and `relevance_metrics.json`. Resumable: rerunning the same command skips job
IDs already present in those output files. Key flags: `--relevance-batch-size`
(default `20`), `--sample-size` (label a random subset instead of everything,
for training the distilled classifier in `scrapers/service/ml/`).

**4. LLM category and skill enrichment**

```bash
python3 -m scrapers.utils.job_enricher \
  --input data/job_classification/av_candidates.jsonl \
  --output-dir data/job_classification
```

Each job is first run through `KeywordCategoryClassifier` - deterministic,
zero-LLM category matching against the same curated vocabulary in
`categories_definition.txt`. Only jobs its vocabulary doesn't cover (an empty
result) fall back to Groq (default 10/request) against the 9-category
taxonomy, extracting categories and skills. Writes `av_jobs.jsonl` - **the
final, complete Silver-layer output** with `categories` and `skills` per job,
each tagged `category_source: "keyword_resolved"` or `"llm_enriched"` - plus
`enrichment_failed_jobs.jsonl` and `enrichment_metrics.json` (which reports
the `keyword_resolved`/`llm_enriched` split for the current run). Also
resumable across interrupted runs. Key flag: `--batch-size` (default `10`;
larger batches amortize the ~850-token taxonomy prompt further but risk
nearing Groq's per-request token ceiling).

**Groq setup for steps 3-4:** set `GROQ_API_KEY` in `scrapers/.env`. It accepts
one key or a comma-separated pool (`key1,key2,key3`); if the active key gets
rate-limited on more than 3 consecutive attempts, the client automatically
rotates to the next key in the pool. See `scrapers/config/groq.py` and
`scrapers/service/llm/groq_client.py`.

## Run the full pipeline end to end

One command chains every stage above (plus scraping and MinIO/bronze ingest
from the [Scrapers section](../README.md#scrapers)):

```bash
python3 -m scrapers.pipeline_main
```

This runs: scrape -> MinIO -> bronze -> Silver (dbt) -> export -> pre-filter ->
LLM relevance -> LLM enrichment, stopping at the first stage that fails so a
bad stage can't silently feed corrupt input downstream.

| Flag | Default | Meaning |
|---|---|---|
| `--company` | all enabled API companies | Passed through to the scrape stage |
| `--skip-scrape` | off | Start from the existing bronze data (skip scrape/MinIO/bronze) |
| `--skip-silver-build` | off | Export whatever `silver.cleaned_job_postings` already has, without rebuilding it |
| `--silver-export-path` | `data/silver_export.jsonl` | Where the Silver export is written |
| `--prefilter-output-dir` | `data/job_prefilter` | Output directory for the pre-filter stage |
| `--classification-output-dir` | `data/job_classification` | Output directory for the relevance and enrichment stages |
| `--prefilter-config` | `scrapers/config/job_prefilter.yaml` | Optional pre-filter rules YAML |

To rerun just the LLM stages against data already sitting in Postgres (for
example after fixing a prompt or rotating Groq keys), skip the first two
stages:

```bash
python3 -m scrapers.pipeline_main --skip-scrape --skip-silver-build
```

The final output of the whole pipeline is
`data/job_classification/av_jobs.jsonl` - AV-relevant jobs with categories and
skills assigned. Loading that into the backend's ERD tables
(`jobposting`/`category`/`skill`/...) is a separate, currently manual step; see
`backend/SILVER_SYNC.md`.

## Building the backend classification handoff

```bash
python3 -m scrapers.utils.build_classification_handoff \
  --input data/job_classification/av_jobs.jsonl \
  --output data/job_classification/handoff.json
```

Reshapes `av_jobs.jsonl` rows into the JSON array `backend/app/import_categories.py`
and `import_skills.py`/`import_salary.py` expect: `deduplication_key`,
`functional_area` (categories, as plain sub_type strings - the backend owns
the static sub_type -> main_type mapping itself, in
`backend/app/config/category_main_types.yaml`, since main_type is a property
of the category and not something a per-job record should be able to set),
`skills`, and salary fields.

**Salary derivation** tries three sources per job, in order, and stops at the
first that resolves - never inventing a number:

1. **Structured API field** - `salary_min`/`salary_max`/`salary_currency`/
   `salary_period`, if the Silver row already has all four (see the bronze
   dbt models, e.g. `greenhouse.sql`'s `pay_input_ranges` parsing). Missing
   any one of the four (a null currency/period the source didn't disclose)
   falls through to the next source instead of importing an incomplete row -
   `salary_sync.sync_salary` rejects a null currency/period, and one bad row
   would otherwise roll back the entire `import_salary` batch.
2. **Regex extraction** (`scrapers/service/silver_cleaning/salary_extractor.py`)
   - a conservative min-max range pattern read directly from the job
   description text, requiring both a recognizable currency and pay period
   nearby before accepting a match.
3. **levels.fyi company average** (`--company-salary-cache`, refreshed via
   `scrapers/utils/refresh_company_salary_cache.py`) - a single company-wide
   median total-compensation figure, not a real range for this posting. This
   fills `salary_average` only, tagged `salary_source: levels_fyi_average`,
   never `salary_min`/`salary_max` (which would make an estimate look like a
   precise disclosed range).

If none of the three resolve, no salary fields are added and the backend
leaves the job's salary columns null.
