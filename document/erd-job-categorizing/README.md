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

See `schema_silver.dbml` for the full schema definition, and `erd_diagram.pdf` for the visual diagram.

### Regenerating `erd_diagram.pdf`
The diagram was originally exported from dbdiagram.io. To regenerate it after editing `schema_silver.dbml` without that web tool:
```bash
npx --yes @softwaretechnik/dbml-renderer -i schema_silver.dbml -f svg -o erd_diagram.svg
```
then render the SVG to PDF (e.g. via headless Chromium's `page.pdf()` - `page.goto()` on a `file://` URL can fail in a sandboxed environment; load the SVG with `page.setContent()` instead, and call `page.emulateMedia({ media: "screen" })` before `page.pdf()` or the print stylesheet renders a blank page).