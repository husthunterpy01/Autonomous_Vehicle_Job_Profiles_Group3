{{ config(materialized="view", schema="bronze", tags=["ats"]) }}

select
    src.source_system as ats_name,
    job->>'id' as source_job_id,
    src.company_name,
    job->>'title' as job_name,
    coalesce(job->>'descriptionPlain', '') as job_description,
    src.headquarter,
    nullif(
        concat_ws(
            ' | ',
            nullif(btrim(job->>'location'), ''),
            (
                select string_agg(nullif(btrim(sec->>'location'), ''), ' | ' order by ord)
                from jsonb_array_elements(coalesce(job->'secondaryLocations', '[]'::jsonb))
                    with ordinality as t(sec, ord)
            )
        ),
        ''
    ) as location,
    job->>'jobUrl' as job_url,
    job->>'publishedAt' as job_uploaded_at,
    job->>'employmentType' as employment_type
from {{ source("bronze", "raw_responses") }} as src
cross join lateral jsonb_array_elements(coalesce(src.body->'jobs', '[]'::jsonb)) as job
where src.source = 'api'
  and src.source_system = 'ashby'
