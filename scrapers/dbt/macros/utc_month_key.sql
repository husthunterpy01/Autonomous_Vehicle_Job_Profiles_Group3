{# yyyymm of a timestamptz in UTC, e.g. 202608 - gold's calendar month. #}
{% macro utc_month_key(column) -%}
    (extract(year from {{ column }} at time zone 'UTC') * 100
        + extract(month from {{ column }} at time zone 'UTC'))::integer
{%- endmacro %}
