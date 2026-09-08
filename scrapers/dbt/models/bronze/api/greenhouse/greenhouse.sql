{{ config(materialized="view", schema="bronze", tags=["ats"]) }}

select
    src.source_system as ats_name,
    job->>'id' as source_job_id,
    src.company_name,
    job->>'title' as job_name,
    job->>'content' as job_description,
    src.headquarter,
    job->'location'->>'name' as location,
    job->>'absolute_url' as job_url,
    job->>'first_published' as job_uploaded_at,
    job->>'employment_type' as employment_type
from {{ source("bronze", "raw_responses") }} as src
cross join lateral jsonb_array_elements(coalesce(src.body->'jobs', '[]'::jsonb)) as job
where src.source = 'api'
  and src.source_system = 'greenhouse'
