{{ config(materialized="table") }}

with src as (
    select *
    from {{ source("bronze", "raw_responses") }}
    where source = 'api'
      and source_system is not null
),

greenhouse as (
    select
        src.source_system as ats_name,
        src.company_name,
        job->>'title' as job_name,
        job->>'content' as job_description,
        src.headquarter,
        job->'location'->>'name' as location,
        job->>'absolute_url' as job_url,
        job->>'first_published' as job_uploaded_at,
        'Full Time' as employment_type
    from src
    cross join lateral jsonb_array_elements(coalesce(src.body->'jobs', '[]'::jsonb)) as job
    where src.source_system = 'greenhouse'
),

lever as (
    select
        src.source_system as ats_name,
        src.company_name,
        job->>'text' as job_name,
        job->>'descriptionPlain' as job_description,
        src.headquarter,
        job->'categories'->>'location' as location,
        job->>'hostedUrl' as job_url,
        job->>'createdAt' as job_uploaded_at,
        coalesce(job->>'workplaceType', 'Full Time') as employment_type
    from src
    cross join lateral jsonb_array_elements(
        case
            when jsonb_typeof(src.body) = 'array' then src.body
            else '[]'::jsonb
        end
    ) as job
    where src.source_system = 'lever'
),

ashby as (
    select
        src.source_system as ats_name,
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
        coalesce(job->>'employmentType', 'Full Time') as employment_type
    from src
    cross join lateral jsonb_array_elements(coalesce(src.body->'jobs', '[]'::jsonb)) as job
    where src.source_system = 'ashby'
),

smartrecruiters as (
    select
        src.source_system as ats_name,
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
        coalesce(job->'typeOfEmployment'->>'label', 'Full Time') as employment_type
    from src
    cross join lateral jsonb_array_elements(coalesce(src.body->'content', '[]'::jsonb)) as job
    where src.source_system in ('smartrecruiters', 'smartrecruiter')
)

select *, now() as ingested_at from greenhouse
union all
select *, now() as ingested_at from lever
union all
select *, now() as ingested_at from ashby
union all
select *, now() as ingested_at from smartrecruiters
