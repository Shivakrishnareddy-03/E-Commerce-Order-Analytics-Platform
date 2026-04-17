select
    customer_id,
    city,
    state,
    zip_code
from {{ ref('stg_customers') }}
