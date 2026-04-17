select
    product_id,
    coalesce(product_category_name, 'unknown') as category_name,
    product_weight as weight_g,
    product_length as length_cm,
    product_height as height_cm
from {{ source('raw', 'products') }}
