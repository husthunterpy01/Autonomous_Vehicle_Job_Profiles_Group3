{{ config(materialized="table", schema="silver") }}

with source_rows as (
    select
        id::text as bronze_id,
        nullif(btrim(source_job_id), '') as source_job_id,
        nullif(btrim(ats_name), '') as ats_name,
        nullif(btrim(regexp_replace(company_name, '\s+', ' ', 'g')), '') as company_name,
        nullif(btrim(regexp_replace(job_name, '\s+', ' ', 'g')), '') as job_name,
        nullif(
            btrim(
                regexp_replace(
                    regexp_replace(
                        replace(replace(replace(replace(replace(job_description,
                            '&lt;', '<'), '&gt;', '>'), '&amp;', '&'), '&nbsp;', ' '), '&#39;', ''''),
                        '<[^>]*>', ' ', 'g'
                    ),
                    '\s+', ' ', 'g'
                )
            ),
            ''
        ) as job_description,
        nullif(btrim(regexp_replace(headquarter, '\s+', ' ', 'g')), '') as headquarter,
        coalesce(
            (
                select array_agg(location order by ordinal)
                from (
                    select distinct on (lower(location)) location, ordinal
                    from (
                        select
                            nullif(btrim(regexp_replace(value, '\s+', ' ', 'g')), '') as location,
                            ordinal
                        from regexp_split_to_table(coalesce(location, ''), '\s*\|\s*')
                            with ordinality as split(value, ordinal)
                    ) normalized_locations
                    where location is not null
                    order by lower(location), ordinal
                ) unique_locations
            ),
            array[]::text[]
        ) as locations,
        null::text as department,
        null::text as team,
        nullif(btrim(job_url), '') as job_url,
        case
            when job_uploaded_at ~ '^\d{13}$'
                then to_timestamp(job_uploaded_at::double precision / 1000.0)
            when job_uploaded_at ~ '^\d{10}(\.\d+)?$'
                then to_timestamp(job_uploaded_at::double precision)
            when job_uploaded_at ~ '^\d{4}-\d{2}-\d{2}'
                then job_uploaded_at::timestamptz
            else null
        end as job_uploaded_at,
        case regexp_replace(lower(btrim(coalesce(employment_type, ''))), '\s+', ' ', 'g')
            when 'fulltime' then 'full-time'
            when 'full time' then 'full-time'
            when 'full-time' then 'full-time'
            when 'parttime' then 'part-time'
            when 'part time' then 'part-time'
            when 'part-time' then 'part-time'
            when 'contractor' then 'contract'
            when 'temp' then 'temporary'
            when 'intern' then 'internship'
            when '' then null
            else regexp_replace(lower(btrim(employment_type)), '\s+', ' ', 'g')
        end as employment_type,
        null::text as workplace_type,
        ingested_at::timestamptz as ingested_at
    from {{ ref("job_postings") }}
),

keyed as (
    select
        *,
        case
            when source_job_id is not null then concat_ws('|', 'source-job-id', lower(ats_name), lower(source_job_id))
            when job_url is not null then concat_ws('|', 'url', lower(ats_name), rtrim(lower(job_url), '/'))
            else concat_ws(
                '|', 'fallback', lower(company_name), lower(job_name),
                coalesce(job_uploaded_at::text, ''),
                array_to_string(
                    (select array_agg(lower(value) order by lower(value)) from unnest(locations) as value),
                    '|'
                )
            )
        end as natural_key,
        num_nonnulls(
            source_job_id, ats_name, company_name, job_name, job_description,
            headquarter, job_url, job_uploaded_at, employment_type, workplace_type
        ) + cardinality(locations) as completeness
    from source_rows
    where job_name is not null and job_description is not null
),

ranked as (
    select
        *,
        row_number() over (
            partition by natural_key
            order by completeness desc, ingested_at desc nulls last, bronze_id desc
        ) as duplicate_rank
    from keyed
)

select
    md5(natural_key) as deduplication_key,
    bronze_id,
    source_job_id,
    ats_name,
    company_name,
    job_name,
    job_description,
    headquarter,
    locations,
    department,
    team,
    job_url,
    job_uploaded_at,
    employment_type,
    workplace_type,
    ingested_at
from ranked
where duplicate_rank = 1
