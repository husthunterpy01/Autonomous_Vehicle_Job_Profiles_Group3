{{ config(materialized="table", schema="gold", tags=["gold"]) }}

-- Calendar months (UTC) that have at least one completed run.
with months as (
    select distinct date_trunc('month', scraped_at at time zone 'UTC')::date as month_start
    from {{ source("silver", "classification_run") }}
    where completed
)

select
    (extract(year from month_start) * 100 + extract(month from month_start))::integer as month_key,
    month_start,
    extract(year from month_start)::smallint as year,
    extract(month from month_start)::smallint as month,
    to_char(month_start, 'Mon YYYY') as label
from months
