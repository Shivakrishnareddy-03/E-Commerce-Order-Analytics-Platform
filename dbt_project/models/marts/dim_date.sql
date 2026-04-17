with date_spine as (
    select
        generate_series(
            (select min(order_date) from {{ ref('stg_orders') }}),
            (select max(order_date) from {{ ref('stg_orders') }}),
            interval '1 day'
        )::date as full_date
)

select
    to_char(full_date, 'YYYYMMDD')::int as date_key,
    full_date,
    extract(year from full_date)::int as date_year,
    extract(quarter from full_date)::int as date_quarter,
    extract(month from full_date)::int as date_month,
    extract(day from full_date)::int as date_day,
    extract(dow from full_date)::int as day_of_week
from date_spine
