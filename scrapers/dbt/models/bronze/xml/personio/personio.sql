{{ config(materialized="view", schema="bronze", tags=["ats"]) }}

-- Personio "workzag-jobs" XML feed. The body is already a JSON array of jobs
-- with bronze-shaped keys, produced by XMLExtractor during BronzeIngest.
select
    src.source_system as ats_name,
    job->>'source_job_id' as source_job_id,
    src.company_name,
    job->>'job_name' as job_name,
    job->>'job_description' as job_description,
    src.headquarter,
    job->>'location' as location,
    job->>'job_url' as job_url,
    job->>'job_uploaded_at' as job_uploaded_at,
    job->>'employment_type' as employment_type
from {{ source("bronze", "raw_responses") }} as src
cross join lateral jsonb_array_elements(
    case
        when jsonb_typeof(src.body) = 'array' then src.body
        else '[]'::jsonb
    end
) as job
where src.source = 'xml'
  and src.source_system = 'personio'
