select
    product_id,
    category_name as category,
    weight_g as weight,
    length_cm as length,
    height_cm as height
from {{ ref('stg_products') }}
