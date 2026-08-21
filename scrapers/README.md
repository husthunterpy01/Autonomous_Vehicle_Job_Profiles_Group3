# BE-1 company job scrapers

This directory implements the BE-1 data-collection task for three approved
company career sources:

| Company | ATS | Scraper |
|---|---|---|
| Waabi | Lever | `waabi_scraper.py` |
| Bosch | SmartRecruiters | `bosch_scraper.py` |
| Stack AV | Greenhouse | `stackav_scraper.py` |

The scrapers only read public job advertisements. They do not submit job
applications or collect applicant information.

## Shared design

`base_scraper.py` contains the common behavior used by every scraper:

- HTTP headers, retries, rate-limit handling, and errors;
- nested HTML/entity decoding;
- required-field and duplicate-ID validation;
- atomic UTF-8 JSON output;
- shared command-line arguments and status messages.

`bronze_storage.py` stores every raw ATS job object immediately after fetching
and before normalization. Each capture is a new UUID-based JSON record under
`data/bronze/`; records are never overwritten or deduplicated. See
[`data/bronze/README.md`](../data/bronze/README.md) for the Bronze schema and
the Silver-layer reading contract.

Each company module contains only its ATS-specific fetching and normalization.
All three produce the same required fields: company, job ID, title, location,
description, posting date, source URL, collection method, ATS, and collection
timestamp. Optional ATS-specific fields are retained when available.

## Run the scrapers

From the repository root:

```powershell
python -m scrapers.waabi_scraper
python -m scrapers.bosch_scraper
python -m scrapers.stackav_scraper
```

Bosch exposes thousands of postings, so its default Sprint 1 batch is the
latest 100. Use a smaller smoke-test batch with:

```powershell
python -m scrapers.bosch_scraper --max-jobs 10
```

Normalized files are written directly under `data/` for local analysis. Raw
append-only records are written below `data/bronze/`. Generated data is ignored
by Git and must not be included in a PR.

## Run automated tests

```powershell
python -m unittest discover -s tests -v
```

The tests cover shared helpers, nested HTML decoding, atomic output, validation,
duplicate detection, and each company's normalization.

## PR evidence checklist

For the BE-1 PR description, attach dated screenshots showing:

1. each scraper completing successfully;
2. the automated test command passing;
3. the local job counts printed by each scraper;
4. `git status --short` confirming `data/*.json` is not included.

Suggested PR title:

```text
[BE-1] Refactor and validate company job scrapers
```

Reference the actual GitHub issue number in the PR body, for example
`Closes #123`, and replace `#123` with the issue corresponding to BE-1.
