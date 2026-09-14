{{ config(materialized="view", schema="bronze", tags=["ats"]) }}

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
    job->>'employment_type' as employment_type,
    -- pay_input_ranges is attached by RawFetch's per-job ?pay_transparency=true
    -- detail GET (rawfetch.py's _expand_greenhouse_postings) - not present on
    -- the plain list response. Values are in cents; most companies disclose
    -- nothing, so this is usually an empty array. Widest range across
    -- multiple disclosed ranges (e.g. one per US state), same handling as
    -- Ashby's multi-component compensationTiers.
    gh_pay.salary_min,
    gh_pay.salary_max,
    gh_pay.salary_currency,
    -- pay_input_ranges is documented/observed as annualized base pay only;
    -- there's no interval field to normalize the way Lever/Ashby have.
    case when gh_pay.salary_min is not null then 'yearly' else null end as salary_period
from {{ source("bronze", "raw_responses") }} as src
cross join lateral jsonb_array_elements(coalesce(src.body->'jobs', '[]'::jsonb)) as job
cross join lateral (
    select
        min(nullif(pay_range->>'min_cents', '')::numeric) / 100.0 as salary_min,
        max(nullif(pay_range->>'max_cents', '')::numeric) / 100.0 as salary_max,
        (array_agg(pay_range->>'currency_type') filter (where pay_range->>'currency_type' is not null))[1] as salary_currency
    from jsonb_array_elements(coalesce(job->'pay_input_ranges', '[]'::jsonb)) as pay_range
) as gh_pay
where src.source = 'api'
  and src.source_system = 'greenhouse'
