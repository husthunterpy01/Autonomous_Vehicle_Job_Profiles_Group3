{{ config(materialized="view", schema="bronze", tags=["ats"]) }}

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
    job->'categories'->>'commitment' as employment_type,
    nullif(job->'salaryRange'->>'min', '')::numeric as salary_min,
    nullif(job->'salaryRange'->>'max', '')::numeric as salary_max,
    job->'salaryRange'->>'currency' as salary_currency,
    -- Lever's own values seen so far: "per-year-salary"; match loosely by
    -- substring so other interval spellings ("per-hour", "per-month-salary",
    -- ...) still normalize instead of silently going null.
    case
        when job->'salaryRange'->>'interval' ilike '%year%' then 'yearly'
        when job->'salaryRange'->>'interval' ilike '%month%' then 'monthly'
        when job->'salaryRange'->>'interval' ilike '%week%' then 'weekly'
        when job->'salaryRange'->>'interval' ilike '%day%' then 'daily'
        when job->'salaryRange'->>'interval' ilike '%hour%' then 'hourly'
        else null
    end as salary_period
from {{ source("bronze", "raw_responses") }} as src
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
where src.source = 'api'
  and src.source_system = 'lever'
