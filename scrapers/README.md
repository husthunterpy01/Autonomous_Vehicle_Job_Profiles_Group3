# Company job scrapers

## Waabi

The Waabi scraper reads currently published vacancies from Waabi's public
Lever Postings API and normalizes them into the project's common job schema.
It does not submit applications or collect applicant information.

From the project root, activate a Python environment and run:

```powershell
conda activate cits5508-a1
python scrapers\waabi_scraper.py
```

The command creates or refreshes:

```text
data\waabi_jobs.json
```

Run the automated checks with:

```powershell
python -m unittest discover -s tests -v
```

The scraper refuses to replace the existing JSON output if the API returns no
jobs, a record is missing a required field, or duplicate job IDs are detected.

## Bosch

Bosch publishes jobs through SmartRecruiters. The Bosch scraper collects the
latest 100 public jobs by default, follows each posting to collect its full
description, and writes:

```text
data\bosch_jobs.json
```

Run the default batch with:

```powershell
python scrapers\bosch_scraper.py
```

Use a smaller batch while developing:

```powershell
python scrapers\bosch_scraper.py --max-jobs 10
```

Or choose a larger batch later:

```powershell
python scrapers\bosch_scraper.py --max-jobs 250
```

## Stack AV

Stack AV publishes jobs through Greenhouse. Greenhouse returns the complete
public board, including job descriptions, in one request. Run:

```powershell
python scrapers\stackav_scraper.py
```

The command creates or refreshes:

```text
data\stackav_jobs.json
```
