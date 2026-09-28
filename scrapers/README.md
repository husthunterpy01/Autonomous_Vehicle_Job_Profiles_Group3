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

Missing employment types are treated as full-time: when a source does not state
one, Silver writes `full-time`. This is a data-processing decision agreed with the
team, made here rather than in the backend so the backend stores what Silver
hands over. The default is applied after deduplication, so a duplicate that did
state a type is still preferred, and the unmodified value remains in
`bronze.job_postings`.

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

**3. Distilled embedding AV-relevance (Groq only for the mid-band)**

The live pipeline scores `llm_candidates.jsonl` with the frozen MiniLM +
logistic probe (`scrapers/service/ml/embedding_classifier.py`). Local
`data/job_classification/relevance_model_embedding.joblib` is used when
present; otherwise weights are downloaded from
[husthunterpy01/av-job-relevance-embedding](https://huggingface.co/husthunterpy01/av-job-relevance-embedding).
Jobs with p≥0.55 go to `av_candidates.jsonl`, p<0.45 to `non_av_jobs.jsonl`,
and 0.45–0.55 to `low_confidence_jobs.jsonl` for Groq.

`relevance_classifier_cli train` and `score` default to `--backend embedding`,
so a flagless CLI run needs `sentence-transformers` (and thus torch), which
`scrapers/requirements.txt` installs. Use `--backend tfidf` for the
sklearn-only path; `--backend setfit` also needs the `setfit` package from
that same file.

```bash
python3 -m scrapers.utils.relevance_classifier_cli score \
  --input data/job_prefilter/llm_candidates.jsonl \
  --output-dir data/job_classification \
  --backend embedding \
  --low-confidence-low 0.45 \
  --low-confidence-high 0.55
```

```bash
python3 -m scrapers.utils.job_classifier \
  --input data/job_classification/low_confidence_jobs.jsonl \
  --output-dir data/job_classification
```

The Groq CLI still screens a whole candidate file (default 20/request) when
you want an LLM-only seed instead of the distilled probe. Writes
`av_candidates.jsonl` (AV-relevant), `non_av_jobs.jsonl`, `relevance_failed_jobs.jsonl`,
and `relevance_metrics.json`. Resumable: rerunning skips job IDs already
present in those output files. Key flags: `--relevance-batch-size`
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
result) fall back to Groq (default 10/request) against the 10-category
taxonomy, extracting categories and skills. Writes `av_jobs.jsonl` - **the
final, complete Silver-layer output** with `categories` and `skills` per job,
each tagged `category_source: "keyword_resolved"` or `"llm_enriched"` - plus
`enrichment_failed_jobs.jsonl` and `enrichment_metrics.json` (which reports
the `keyword_resolved`/`llm_enriched` split for the current run). Also
resumable across interrupted runs. Key flag: `--batch-size` (default `10`;
larger batches amortize the ~850-token taxonomy prompt further but risk
nearing Groq's per-request token ceiling).

**Groq setup for the mid-band and enrichment stages:** set `GROQ_API_KEY` in `scrapers/.env`. It accepts
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
embedding relevance (Groq only for p in 0.45–0.55) -> LLM enrichment, stopping
at the first stage that fails so a bad stage can't silently feed corrupt input
downstream.

| Flag | Default | Meaning |
|---|---|---|
| `--company` | all enabled API companies | Passed through to the scrape stage |
| `--skip-scrape` | off | Start from the existing bronze data (skip scrape/MinIO/bronze) |
| `--skip-silver-build` | off | Export whatever `silver.cleaned_job_postings` already has, without rebuilding it |
| `--silver-export-path` | `data/silver_export.jsonl` | Where the Silver export is written |
| `--prefilter-output-dir` | `data/job_prefilter` | Output directory for the pre-filter stage |
| `--classification-output-dir` | `data/job_classification` | Output directory for the relevance and enrichment stages |
| `--prefilter-config` | `scrapers/config/job_prefilter.yaml` | Optional pre-filter rules YAML |
| `--embedding-hf-repo-id` | `husthunterpy01/av-job-relevance-embedding` | Hub repo for the embedding probe when no local joblib exists |

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

**Removing dropped jobs' old labels.** Jobs the pipeline drops (a role that fits
no category goes to `no_category_jobs.jsonl`, a non-engineering one to
`non_engineering_jobs.jsonl`, an AV-irrelevant one to `non_av_jobs.jsonl`) never
reach `av_jobs.jsonl`, so the handoff above never mentions them and a job
labeled on an earlier run (often Infrastructure) would keep that label forever.
Pass them with `--dropped` to also write a **separate** clear-only file:

```bash
python3 -m scrapers.utils.build_classification_handoff \
  --input data/job_classification/av_jobs.jsonl \
  --dropped data/job_classification/no_category_jobs.jsonl \
  --dropped data/job_classification/non_engineering_jobs.jsonl \
  --output data/job_classification/handoff.json \
  --dropped-output data/job_classification/handoff_dropped.json
```

`handoff_dropped.json` holds `{"deduplication_key": ..., "functional_area": []}`
rows and must go to `python -m app.import_categories` **only** - the backend
treats `[]` as "clear" and skips a clear row whose job was never inserted, but
`import_skills`/`import_salary` would fail on those unknown jobs. A job that is
accepted in the same run is not cleared. This removes the category label only;
skills and salary are left as they are.

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
