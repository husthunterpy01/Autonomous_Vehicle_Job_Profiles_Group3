# ERD - Job Categorizing (Silver Layer)

## Overview
This ERD covers the Silver layer (core detail tables) for the AV job scraping project.
The Gold layer (e.g., trending data marts) will be maintained separately (to be modified and improved).

## Entities
- Company / CompanyLocation
- JobPosting
- Category / JobCategory
- Skill / JobSkill
- ScrapeLog

## Design notes
- Most JobPosting fields are nullable since job posting structures vary significantly across company websites.
- `raw_description` and `source_url` are required fields — they serve as the fallback for LLM-based extraction regardless of site structure.
- UUIDs are used as primary keys instead of auto-increment integers to support future scalability (e.g. merging data from distributed scraping runs).
- `skill_type` uses a predefined Enum to keep values consistent.

## Salary
Salary lives on `JobPosting`, one set of values per job posting. There is no separate salary table.

| Column | Meaning |
|---|---|
| `salary_min` / `salary_max` | A salary range published for this job, from an ATS API field or extracted from the description. Description extraction only accepts a real range; a single figure such as "up to $200,000" is skipped rather than turned into a range. |
| `salary_average` | The levels.fyi company-wide estimate, used only when the job publishes no salary. |
| `salary_currency` | Currency code as published. |
| `salary_period` | `yearly`, `monthly`, `weekly`, `daily` or `hourly`. |
| `salary_source` | `api`, `regex` or `levels_fyi_average`. |

Decisions:
- **A job has either a published range or an estimate, never both.** `salary_average` is not an average of `salary_min` and `salary_max`, and it is not computed from them.
- **No currency conversion.** Values are stored and shown in their original currency, so they always match the source.
- **The levels.fyi estimate is company-wide.** Every job at the same company gets the same figure, regardless of title or location. The frontend prefixes estimates with `~` so they are not read as published salaries.
- **Salaries are only comparable within one pay period.** The job list's `min_salary`/`max_salary` filters therefore require `salary_period`, and salary sorting is not offered.
- **Missing salary is null.** Nothing is guessed when a job publishes no salary and no estimate is available.

Rules enforced by the database (`backend/app/sql/be13_salary_constraints_migration.sql`, mirrored in the ORM), on top of the checks in `backend/app/services/salary_sync.py`:
- salary values are positive, and `salary_min <= salary_max`;
- a job has a published range or `salary_average`, never both;
- any salary has `salary_currency`, `salary_period` and `salary_source` set.

The allowed values for period and source are still validated in `salary_sync.py` only.

Migrations, applied after `be9_migration.sql`:
1. `be10_salary_migration.sql` adds `salary_min`, `salary_max`, `salary_period` and `salary_source`. Rollback: `be10_salary_migration_rollback.sql`, which drops those columns and their data.
2. `be13_salary_constraints_migration.sql` adds the constraints. It refuses to apply while any existing row breaks a rule, so remove such rows first - in particular the 12 demo jobs from `seed_companies.sql` (job IDs starting `33333333-`), whose salary has no period or source. Rollback: `be13_salary_constraints_rollback.sql`, which removes the constraints without changing data.

`seed_companies.sql` is for local testing only and no longer sets a salary on its demo jobs.

See `schema_silver.dbml` for the full schema definition, and `erd_diagram.pdf` for the visual diagram.