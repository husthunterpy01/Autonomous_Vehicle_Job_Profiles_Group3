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

See `schema_silver.dbml` for the full schema definition, and `erd_diagram.pdf` for the visual diagram.