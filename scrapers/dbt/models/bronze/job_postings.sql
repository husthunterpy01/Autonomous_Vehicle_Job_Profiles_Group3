{{ config(materialized="table", schema="bronze") }}

with src as (
    select *
    from {{ source("bronze", "raw_responses") }}
    where source = 'api'
      and source_system is not null
),

greenhouse as (
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
    from src
    cross join lateral jsonb_array_elements(coalesce(src.body->'jobs', '[]'::jsonb)) as job
    where src.source_system = 'greenhouse'
),

lever as (
    select
        src.source_system as ats_name,
        job->>'id' as source_job_id,
        src.company_name,
        job->>'text' as job_name,
        concat_ws(
            E'\n\n',
            nullif(btrim(lever_jd.role_body), ''),
            nullif(btrim(lever_jd.lists_text), '')
        ) as job_description,
        src.headquarter,
        job->'categories'->>'location' as location,
        job->>'hostedUrl' as job_url,
        job->>'createdAt' as job_uploaded_at,
        job->'categories'->>'commitment' as employment_type
    from src
    cross join lateral jsonb_array_elements(
        case
            when jsonb_typeof(src.body) = 'array' then src.body
            else '[]'::jsonb
        end
    ) as job
    cross join lateral (
        select
            coalesce(
                nullif(btrim(coalesce(job->>'descriptionBodyPlain', '')), ''),
                case
                    when nullif(btrim(coalesce(job->>'openingPlain', '')), '') is not null
                     and starts_with(
                         btrim(coalesce(job->>'descriptionPlain', '')),
                         btrim(coalesce(job->>'openingPlain', ''))
                     )
                    then btrim(substr(
                        btrim(coalesce(job->>'descriptionPlain', '')),
                        char_length(btrim(coalesce(job->>'openingPlain', ''))) + 1
                    ))
                    else btrim(coalesce(job->>'descriptionPlain', ''))
                end
            ) as role_body,
            (
                select string_agg(
                    concat_ws(
                        E'\n',
                        nullif(btrim(coalesce(elem->>'text', '')), ''),
                        nullif(btrim(coalesce(elem->>'content', '')), '')
                    ),
                    E'\n\n'
                    order by ord
                )
                from jsonb_array_elements(coalesce(job->'lists', '[]'::jsonb))
                    with ordinality as t(elem, ord)
                where lower(coalesce(elem->>'text', '')) not like '%salary%'
            ) as lists_text
    ) as lever_jd
    where src.source_system = 'lever'
),

ashby as (
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
    from src
    cross join lateral jsonb_array_elements(coalesce(src.body->'jobs', '[]'::jsonb)) as job
    where src.source_system = 'ashby'
),

smartrecruiters as (
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
        job->'typeOfEmployment'->>'label' as employment_type
    from src
    cross join lateral jsonb_array_elements(coalesce(src.body->'content', '[]'::jsonb)) as job
    where src.source_system in ('smartrecruiters', 'smartrecruiter')
),

parsed as (
    select * from greenhouse
    union all
    select * from lever
    union all
    select * from ashby
    union all
    select * from smartrecruiters
)

select
    row_number() over (
        order by company_name, coalesce(job_url, ''), job_name
    ) as id,
    parsed.*,
    now() as ingested_at
from parsed
