with order_payments as (
    select
        order_id,
        sum(payment_value) as total_payment_value
    from {{ ref('stg_payments') }}
    group by order_id
),

order_reviews as (
    select
        order_id,
        avg(review_score) as avg_review_score
    from {{ ref('stg_reviews') }}
    group by order_id
)

select
    oi.order_id,
    oi.order_item_id,
    o.customer_id,
    oi.product_id,
    oi.seller_id,
    oi.price,
    oi.shipping_charges,
    o.order_status,
    to_char(o.order_date, 'YYYYMMDD')::int as date_key,
    op.total_payment_value as payment_value,
    coalesce(orv.avg_review_score, 0) as review_score
from {{ ref('stg_order_items') }} as oi
inner join {{ ref('stg_orders') }} as o
    on oi.order_id = o.order_id
left join order_payments as op
    on oi.order_id = op.order_id
left join order_reviews as orv
    on oi.order_id = orv.order_id
