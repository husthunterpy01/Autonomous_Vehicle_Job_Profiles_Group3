{{ config(materialized="table", schema="gold", tags=["gold"]) }}

-- One row per (normalized name, skill type); the display name comes from
-- the newest completed run that listed the skill.
with skills as (
    select s.skill_name, s.skill_type, s.display_name, s.scraped_at
    from {{ source("silver", "classified_job_skill") }} as s
    join {{ source("silver", "classification_run") }} as r using (scraped_at)
    where r.completed
)

select distinct on (skill_name, skill_type)
    md5(skill_name || '|' || skill_type) as skill_key,
    skill_name as normalized_name,
    skill_type,
    display_name
from skills
order by skill_name, skill_type, scraped_at desc, display_name
