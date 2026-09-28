{{ config(materialized="table", schema="gold", tags=["gold"]) }}

-- One row per job (deduplication_key, stable across scrapes). Title and
-- main_type are type 1: the newest completed run wins, whatever order the
-- runs were ingested in.
with jobs as (
    select j.deduplication_key, j.job_title, j.main_type, j.scraped_at
    from {{ source("silver", "classified_job") }} as j
    join {{ source("silver", "classification_run") }} as r using (scraped_at)
    where r.completed
),

seen as (
    select deduplication_key, min(scraped_at) as first_seen_at, max(scraped_at) as last_seen_at
    from jobs
    group by deduplication_key
),

latest as (
    select distinct on (deduplication_key) deduplication_key, job_title, main_type
    from jobs
    order by deduplication_key, scraped_at desc
)

select l.deduplication_key, l.job_title as title, l.main_type, s.first_seen_at, s.last_seen_at
from latest as l
join seen as s using (deduplication_key)
