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
    job->>'employmentType' as employment_type,
    -- compensationTiers was empty/null on every live posting checked this
    -- session (most companies set shouldDisplayCompensationOnJobPostings:
    -- false), so this is built from Ashby's documented public job-board
    -- schema rather than a verified populated sample - re-check field names
    -- (components[].minValue/maxValue/currencyCode/interval/compensationType)
    -- against a real populated posting once one is found. Widest range
    -- across Salary-type components across all tiers, per the same
    -- multi-tier handling as Greenhouse's pay_input_ranges.
    ashby_comp.salary_min,
    ashby_comp.salary_max,
    ashby_comp.salary_currency,
    ashby_comp.salary_period
from {{ source("bronze", "raw_responses") }} as src
cross join lateral jsonb_array_elements(coalesce(src.body->'jobs', '[]'::jsonb)) as job
cross join lateral (
    select
        min(nullif(component->>'minValue', '')::numeric) as salary_min,
        max(nullif(component->>'maxValue', '')::numeric) as salary_max,
        (array_agg(component->>'currencyCode') filter (where component->>'currencyCode' is not null))[1] as salary_currency,
        (array_agg(
            case
                when component->>'interval' ilike '%year%' then 'yearly'
                when component->>'interval' ilike '%month%' then 'monthly'
                when component->>'interval' ilike '%week%' then 'weekly'
                when component->>'interval' ilike '%day%' then 'daily'
                when component->>'interval' ilike '%hour%' then 'hourly'
            end
        ) filter (where component->>'interval' is not null))[1] as salary_period
    from jsonb_array_elements(coalesce(job->'compensation'->'compensationTiers', '[]'::jsonb)) as tier
    cross join lateral jsonb_array_elements(coalesce(tier->'components', '[]'::jsonb)) as component
    where lower(coalesce(component->>'compensationType', '')) = 'salary'
) as ashby_comp
where src.source = 'api'
  and src.source_system = 'ashby'
