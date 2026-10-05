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
- A job's `Category` links may carry multiple sub_types, but the scraper enforces that they all share one `main_type` (see `scrapers/service/llm/category_hierarchy.py`) - a job belongs to exactly one technical area, never a mix.

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
- **The job list's `salary_min`/`salary_max` filters compare an annualized, USD-converted figure (BE-22)**, not the raw `salary_min`/`salary_max` columns - the same conversion `SalaryStatsService` uses for Top Paid Jobs (`app/services/salary_conversion.py`), so the filter works correctly regardless of a job's actual pay period or currency and no longer requires `salary_period` to be set alongside it. Salary sorting is still not offered - the conversion isn't exposed as a displayable value.
- **Two salary filters with different meanings.** On `GET /api/v1/jobs`, `has_salary=true` matches any salary information, including a levels.fyi estimate. `salary_disclosed=true` matches only a range the employer published, in any pay period. The homepage's Featured jobs use `salary_disclosed`, because the client wants employers that publish pay to stand out.
- **Missing salary is null.** Nothing is guessed when a job publishes no salary and no estimate is available.

Rules enforced by the database, on top of the checks in `backend/app/services/salary_sync.py`. They are defined only in `backend/app/sql/be13_salary_constraints_migration.sql`, which is the source of truth; the ORM model does not declare them:
- salary values are positive, and `salary_min <= salary_max`;
- a job has a published range or `salary_average`, never both;
- any salary has `salary_currency`, `salary_period` and `salary_source` set.

The allowed values for period and source are still validated in `salary_sync.py` only.

Migrations, applied after `be9_migration.sql`:
1. `be10_salary_migration.sql` adds `salary_min`, `salary_max`, `salary_period` and `salary_source`. Rollback: `be10_salary_migration_rollback.sql`, which drops those columns and their data.
2. `be13_salary_constraints_migration.sql` adds the constraints. It refuses to apply while any existing row breaks a rule, so remove such rows first - in particular the 12 demo jobs from `seed_companies.sql` (job IDs starting `33333333-`), whose salary has no period or source. Rollback: `be13_salary_constraints_rollback.sql`, which removes the constraints without changing data.

A database created from scratch with `init_db()` does not get these constraints from the ORM, so apply `be13_salary_constraints_migration.sql` to it as well.

`seed_companies.sql` is for local testing only and no longer sets a salary on its demo jobs.

### Job location countries (BE-21, #112)
`Location.country` holds the country each `Location` label names, for the exact country filter (`GET /api/v1/jobs?country=`) and the list of countries with jobs (`GET /api/v1/jobs/countries`). The looser `location` text filter is unchanged.

Decisions:
- **A column on `location`.** The Silver sync splits "London; Sunnyvale" into separate locations, so one place has one country and a job belongs to the country of each of its locations. A label that names several countries ("Remote US & Canada") or none gets no country (BE-31 replaced the BE-21 `location_country` table).
- **Derived from the label, never typed in.** `backend/app/utils/location_country.py` reads country names and aliases, US state names, a small city table, and two-letter state codes only as a last resort, because "IL", "DE", "IN" and "CA" are also country codes. A label with no country in it, such as a bare "Remote", gets no row rather than a guess.
- **The list follows where the jobs are,** not where companies have their headquarters, as agreed with the client lead. So it grows as new countries appear in the data.

Migration: `be31_location_country_column_migration.sql` adds `location.country` (and its index), carries over what the BE-21 `location_country` table held and drops that table; then `python -m app.refresh_location_countries` fills the rest. Run the command again whenever the rules change; new locations get their country during sync. Rollback: `be31_location_country_column_rollback.sql`. A new database gets the column from `init_db()` because it is part of the ORM model, but an existing one needs the migration.

See `schema_silver.dbml` for the full schema definition, and `erd_diagram.pdf` for the visual diagram.

### Regenerating `erd_diagram.pdf`
The diagram was originally exported from dbdiagram.io. To regenerate it after editing `schema_silver.dbml` without that web tool:
```bash
npx --yes @softwaretechnik/dbml-renderer -i schema_silver.dbml -f svg -o erd_diagram.svg
```
then render the SVG to PDF (e.g. via headless Chromium's `page.pdf()` - `page.goto()` on a `file://` URL can fail in a sandboxed environment; load the SVG with `page.setContent()` instead, and call `page.emulateMedia({ media: "screen" })` before `page.pdf()` or the print stylesheet renders a blank page).
