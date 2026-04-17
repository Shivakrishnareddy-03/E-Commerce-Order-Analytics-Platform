select
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_delivered_timestamp,
    order_purchase_timestamp::date as order_date
from {{ source('raw', 'orders') }}
