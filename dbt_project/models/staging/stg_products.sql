select
    product_id,
    product_weight as weight_g,
    product_length as length_cm,
    product_height as height_cm,
    coalesce(product_category_name, 'unknown') as category_name
from {{ source('raw', 'products') }}
