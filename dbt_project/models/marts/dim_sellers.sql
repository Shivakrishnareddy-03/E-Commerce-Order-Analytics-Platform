select
    seller_id,
    city,
    state,
    zip_code
from {{ ref('stg_sellers') }}
