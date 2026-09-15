{{ config(materialized="view", schema="bronze", tags=["ats"]) }}

-- Workable widget API returns {"jobs": [...]} with a flat job object each.
select
    src.source_system as ats_name,
    job->>'shortcode' as source_job_id,
    src.company_name,
    job->>'title' as job_name,
    job->>'description' as job_description,
    src.headquarter,
    nullif(
        concat_ws(
            ', ',
            nullif(btrim(job->>'city'), ''),
            nullif(btrim(job->>'state'), ''),
            nullif(btrim(job->>'country'), '')
        ),
        ''
    ) as location,
    coalesce(nullif(job->>'shortlink', ''), job->>'url') as job_url,
    coalesce(nullif(job->>'published_on', ''), job->>'created_at') as job_uploaded_at,
    job->>'employment_type' as employment_type,
    -- No structured salary field on this ATS; carried as null to keep the
    -- column set matching across job_postings.sql's UNION ALL.
    null::numeric as salary_min,
    null::numeric as salary_max,
    null::text as salary_currency,
    null::text as salary_period
from {{ source("bronze", "raw_responses") }} as src
cross join lateral jsonb_array_elements(coalesce(src.body->'jobs', '[]'::jsonb)) as job
where src.source = 'api'
  and src.source_system = 'workable'
