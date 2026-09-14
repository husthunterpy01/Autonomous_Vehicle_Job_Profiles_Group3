{{ config(materialized="view", schema="bronze", tags=["ats"]) }}

select
    src.source_system as ats_name,
    job->>'id' as source_job_id,
    src.company_name,
    job->>'name' as job_name,
    coalesce(
        nullif(
            concat_ws(
                E'\n',
                job->'jobAd'->'sections'->'companyDescription'->>'text',
                job->'jobAd'->'sections'->'jobDescription'->>'text',
                job->'jobAd'->'sections'->'qualifications'->>'text',
                job->'jobAd'->'sections'->'additionalInformation'->>'text'
            ),
            ''
        ),
        job->>'content'
    ) as job_description,
    src.headquarter,
    job->'location'->>'fullLocation' as location,
    coalesce(job->>'postingUrl', job->>'absolute_url') as job_url,
    job->>'releasedDate' as job_uploaded_at,
    job->'typeOfEmployment'->>'label' as employment_type,
    -- No structured salary field on this ATS; carried as null to keep the
    -- column set matching across job_postings.sql's UNION ALL.
    null::numeric as salary_min,
    null::numeric as salary_max,
    null::text as salary_currency,
    null::text as salary_period
from {{ source("bronze", "raw_responses") }} as src
cross join lateral jsonb_array_elements(coalesce(src.body->'content', '[]'::jsonb)) as job
where src.source = 'api'
  and src.source_system in ('smartrecruiters', 'smartrecruiter')
