-- ============================================================
-- ADVANCED ANALYTICAL QUERIES
-- Uses CTEs and Window Functions on the Olist E-Commerce dataset
-- ============================================================


-- ============================================================
-- QUERY 1: Monthly Revenue Trend with Month-over-Month Growth
-- Techniques: CTE, LAG() window function
-- ============================================================

with monthly_revenue as (
    select
        date_trunc('month', o.order_purchase_timestamp)::date as revenue_month,
        sum(p.payment_value) as total_revenue,
        count(distinct o.order_id) as total_orders
    from orders o
    join payments p on o.order_id = p.order_id
    where o.order_status != 'canceled'
    group by 1
),

revenue_with_growth as (
    select
        revenue_month,
        total_revenue,
        total_orders,
        lag(total_revenue) over (order by revenue_month) as prev_month_revenue,
        round(
            (total_revenue - lag(total_revenue) over (order by revenue_month))
            / nullif(lag(total_revenue) over (order by revenue_month), 0) * 100,
            2
        ) as mom_growth_pct
    from monthly_revenue
)

select *
from revenue_with_growth
order by revenue_month;


-- ============================================================
-- QUERY 2: Top 5 Sellers per State by Revenue with Cumulative Totals
-- Techniques: CTE, RANK(), SUM() OVER (cumulative window)
-- ============================================================

with seller_revenue as (
    select
        s.seller_state,
        s.seller_city,
        s.seller_id,
        sum(oi.price + oi.shipping_charges) as total_revenue,
        count(distinct oi.order_id) as orders_fulfilled,
        avg(r.review_score) as avg_review_score
    from sellers s
    join order_items oi on s.seller_id = oi.seller_id
    join orders o on oi.order_id = o.order_id
    left join reviews r on o.order_id = r.order_id
    group by s.seller_state, s.seller_city, s.seller_id
),

ranked_sellers as (
    select
        seller_state,
        seller_city,
        seller_id,
        total_revenue,
        orders_fulfilled,
        round(avg_review_score::numeric, 2) as avg_review_score,
        rank() over (
            partition by seller_state
            order by total_revenue desc
        ) as state_rank,
        sum(total_revenue) over (
            partition by seller_state
            order by total_revenue desc
            rows unbounded preceding
        ) as cumulative_state_revenue
    from seller_revenue
)

select *
from ranked_sellers
where state_rank <= 5
order by seller_state, state_rank;


-- ============================================================
-- QUERY 3: Customer Cohort Retention Analysis
-- Techniques: Multiple CTEs, EXTRACT + AGE date math, COUNT DISTINCT
-- ============================================================

with customer_first_order as (
    select
        customer_id,
        date_trunc('month', min(order_purchase_timestamp))::date as cohort_month
    from orders
    group by customer_id
),

customer_orders as (
    select
        o.customer_id,
        cfo.cohort_month,
        date_trunc('month', o.order_purchase_timestamp)::date as order_month,
        (
            extract(year from age(
                date_trunc('month', o.order_purchase_timestamp),
                cfo.cohort_month
            )) * 12
            + extract(month from age(
                date_trunc('month', o.order_purchase_timestamp),
                cfo.cohort_month
            ))
        )::int as months_since_first
    from orders o
    join customer_first_order cfo on o.customer_id = cfo.customer_id
),

cohort_sizes as (
    select
        cohort_month,
        count(distinct customer_id) as cohort_size
    from customer_first_order
    group by cohort_month
),

retention as (
    select
        co.cohort_month,
        co.months_since_first,
        count(distinct co.customer_id) as active_customers
    from customer_orders co
    group by co.cohort_month, co.months_since_first
)

select
    r.cohort_month,
    cs.cohort_size,
    r.months_since_first,
    r.active_customers,
    round(r.active_customers::numeric / cs.cohort_size * 100, 2) as retention_pct
from retention r
join cohort_sizes cs on r.cohort_month = cs.cohort_month
order by r.cohort_month, r.months_since_first;
