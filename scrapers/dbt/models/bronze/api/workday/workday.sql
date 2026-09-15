{{ config(materialized="view", schema="bronze", tags=["ats"]) }}

-- Workday: the CXS /jobs list carries only summary fields; the full posting is
-- in job->'jobPostingDetail'->'jobPostingInfo', attached by RawFetch's per-job
-- detail GET. That detail can be missing if the GET failed, hence the coalesces.
with postings as (
    select
        src.source_system,
        src.company_name,
        src.headquarter,
        job,
        coalesce(job->'jobPostingDetail'->'jobPostingInfo', '{}'::jsonb) as info
    from {{ source("bronze", "raw_responses") }} as src
    cross join lateral jsonb_array_elements(
        coalesce(src.body->'jobPostings', '[]'::jsonb)
    ) as job
    where src.source = 'api'
      and src.source_system = 'workday'
)

select
    source_system as ats_name,
    coalesce(
        nullif(info->>'jobReqId', ''),
        job->'bulletFields'->>0,
        regexp_replace(job->>'externalPath', '^.*/', '')
    ) as source_job_id,
    company_name,
    coalesce(nullif(info->>'title', ''), job->>'title') as job_name,
    info->>'jobDescription' as job_description,
    headquarter,
    coalesce(nullif(info->>'location', ''), nullif(job->>'locationsText', '')) as location,
    coalesce(nullif(info->>'externalUrl', ''), job->>'externalPath') as job_url,
    coalesce(nullif(info->>'startDate', ''), nullif(info->>'postedOn', '')) as job_uploaded_at,
    info->>'timeType' as employment_type,
    -- No structured salary field on this ATS; carried as null to keep the
    -- column set matching across job_postings.sql's UNION ALL.
    null::numeric as salary_min,
    null::numeric as salary_max,
    null::text as salary_currency,
    null::text as salary_period
from postings
