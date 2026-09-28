{{ config(materialized="table", schema="gold", tags=["gold"]) }}

-- Grain: (month, job, skill) - "this job listed this skill in this month",
-- with the first and last completed run that saw it. Repeated runs in a
-- month only move first/last seen, so rows grow with jobs x skills per
-- month, not with the number of runs.
select
    {{ utc_month_key("s.scraped_at") }} as month_key,
    s.deduplication_key,
    md5(s.skill_name || '|' || s.skill_type) as skill_key,
    min(s.scraped_at) as first_seen_at,
    max(s.scraped_at) as last_seen_at
from {{ source("silver", "classified_job_skill") }} as s
join {{ source("silver", "classification_run") }} as r using (scraped_at)
where r.completed
group by 1, 2, 3
