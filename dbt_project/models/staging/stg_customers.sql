-- Staging model: clean and rename raw customer columns
select
    customer_id,
    customer_zip_code_prefix as zip_code,
    customer_city as city,
    customer_state as state
from {{ source('raw', 'customers') }}
