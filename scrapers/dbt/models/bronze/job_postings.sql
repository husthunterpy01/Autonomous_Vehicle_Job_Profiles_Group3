{{ config(materialized="table", schema="bronze") }}

with parsed as (
    select * from {{ ref("greenhouse") }}
    union all
    select * from {{ ref("lever") }}
    union all
    select * from {{ ref("ashby") }}
    union all
    select * from {{ ref("smartrecruiters") }}
    union all
    select * from {{ ref("workday") }}
    union all
    select * from {{ ref("workable") }}
    union all
    select * from {{ ref("comeet") }}
    union all
    select * from {{ ref("personio") }}
    union all
    select * from {{ ref("html_jobs") }}
)

select
    row_number() over (
        order by company_name, coalesce(job_url, ''), job_name
    ) as id,
    -- The ATS-native posting id on its own (Greenhouse/SmartRecruiters numbers,
    -- Lever/Ashby UUIDs, ...). Falls back to the job URL, then a content hash,
    -- only when the ATS gives no id, so the column is never null.
    coalesce(
        nullif(btrim(source_job_id), ''),
        nullif(btrim(job_url), ''),
        md5(coalesce(company_name, '') || '|' || coalesce(job_name, ''))
    ) as job_id,
    parsed.*,
    now() as ingested_at
from parsed
