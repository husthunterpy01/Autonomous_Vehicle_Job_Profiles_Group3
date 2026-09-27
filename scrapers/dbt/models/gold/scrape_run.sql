{{ config(materialized="table", schema="gold", tags=["gold"]) }}

-- Completed scrape runs, so gold is self-contained: it is copied on its own
-- to the gold database, where the silver tables don't exist.
-- classifier_version explains a step in the chart when the classifier changes.
select
    scraped_at,
    {{ utc_month_key("scraped_at") }} as month_key,
    source,
    classifier_version,
    jobs_seen
from {{ source("silver", "classification_run") }}
where completed
