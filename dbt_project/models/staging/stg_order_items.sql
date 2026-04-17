select
    order_id,
    order_item_id,
    product_id,
    seller_id,
    price,
    shipping_charges
from {{ source('raw', 'order_items') }}
