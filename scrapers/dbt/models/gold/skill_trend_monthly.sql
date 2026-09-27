{{ config(materialized="view", schema="gold", tags=["gold"]) }}

-- Monthly skill demand from a month-end snapshot: each month is compared by
-- the jobs in its latest completed run. A fact belongs to that snapshot
-- exactly when its last_seen_at equals the run's scraped_at.
with month_snapshot as (
    select {{ utc_month_key("scraped_at") }} as month_key, max(scraped_at) as snapshot_at
    from {{ source("silver", "classification_run") }}
    where completed
    group by 1
),

snapshot_facts as (
    select f.month_key, f.deduplication_key, f.skill_key, s.snapshot_at
    from {{ ref("fact_job_skill_month") }} as f
    join month_snapshot as s
      on s.month_key = f.month_key
     and f.last_seen_at = s.snapshot_at
),

per_skill as (
    select month_key, snapshot_at, skill_key, count(distinct deduplication_key) as job_count
    from snapshot_facts
    group by month_key, snapshot_at, skill_key
),

per_month as (
    select month_key, count(distinct deduplication_key) as jobs_with_skills
    from snapshot_facts
    group by month_key
)

select
    p.month_key,
    m.month_start as month,
    m.label as month_label,
    p.snapshot_at,
    k.display_name as skill_name,
    k.normalized_name as skill_normalized_name,
    k.skill_type,
    p.job_count,
    t.jobs_with_skills,
    round(p.job_count::numeric / t.jobs_with_skills, 4) as share,
    row_number() over (
        partition by p.month_key
        order by p.job_count desc, k.normalized_name, k.skill_type
    ) as rank
from per_skill as p
join per_month as t using (month_key)
join {{ ref("dim_month") }} as m using (month_key)
join {{ ref("dim_skill") }} as k using (skill_key)
