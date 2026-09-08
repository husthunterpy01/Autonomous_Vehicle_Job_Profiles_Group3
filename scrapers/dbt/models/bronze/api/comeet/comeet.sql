{{ config(materialized="view", schema="bronze", tags=["ats"]) }}

-- Comeet careers-api returns a flat JSON array of positions; the long-form
-- description lives in job->'details' as ordered {name, value} sections.
select
    src.source_system as ats_name,
    job->>'uid' as source_job_id,
    src.company_name,
    job->>'name' as job_name,
    (
        select string_agg(
            concat_ws(E'\n', nullif(btrim(sec->>'name'), ''), sec->>'value'),
            E'\n\n'
            order by (sec->>'order')::int
        )
        from jsonb_array_elements(coalesce(job->'details', '[]'::jsonb)) as sec
        where nullif(btrim(coalesce(sec->>'value', '')), '') is not null
    ) as job_description,
    src.headquarter,
    job->'location'->>'name' as location,
    coalesce(job->>'position_url', job->>'url_comeet_hosted_page') as job_url,
    job->>'time_updated' as job_uploaded_at,
    job->>'employment_type' as employment_type
from {{ source("bronze", "raw_responses") }} as src
cross join lateral jsonb_array_elements(
    case
        when jsonb_typeof(src.body) = 'array' then src.body
        else '[]'::jsonb
    end
) as job
where src.source = 'api'
  and src.source_system = 'comeet'
