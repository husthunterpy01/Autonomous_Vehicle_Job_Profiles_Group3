{{ config(materialized="table", schema="bronze") }}

with parsed as (
    select * from {{ ref("greenhouse") }}
    union all
    select * from {{ ref("lever") }}
    union all
    select * from {{ ref("ashby") }}
    union all
    select * from {{ ref("smartrecruiters") }}
)

select
    row_number() over (
        order by company_name, coalesce(job_url, ''), job_name
    ) as id,
    parsed.*,
    now() as ingested_at
from parsed
