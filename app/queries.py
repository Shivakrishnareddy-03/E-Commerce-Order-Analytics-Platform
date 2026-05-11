"""
SQL query builders for the Streamlit dashboard.

All queries use a `filtered_orders` CTE as the entry point so that date,
state, and category filters are applied consistently and payment values are
never double-counted across queries.

Note on SQL injection: filter values (states, categories) are loaded
directly from the database and presented as multiselect options, so they
are never free-form user input.
"""


def _filtered_orders_cte(start, end, states, categories):
    """
    Returns a WITH clause that produces a de-duplicated set of order rows
    matching the selected date range, customer states, and product categories.
    """
    state_join = (
        "JOIN customers c ON o.customer_id = c.customer_id"
        if states else ""
    )
    cat_joins = (
        "JOIN order_items oi ON o.order_id = oi.order_id\n"
        "        JOIN products pr ON oi.product_id = pr.product_id"
        if categories else ""
    )

    conditions = [
        f"o.order_purchase_timestamp BETWEEN '{start}' AND '{end}'"
    ]
    if states:
        s = "', '".join(states)
        conditions.append(f"c.customer_state IN ('{s}')")
    if categories:
        c = "', '".join(categories)
        conditions.append(f"pr.product_category_name IN ('{c}')")

    where = "\n          AND ".join(conditions)

    return f"""
    WITH filtered_orders AS (
        SELECT DISTINCT
            o.order_id,
            o.customer_id,
            o.order_status,
            o.order_purchase_timestamp
        FROM orders o
        {state_join}
        {cat_joins}
        WHERE {where}
    )"""


def kpis_query(start, end, states, categories):
    cte = _filtered_orders_cte(start, end, states, categories)
    return f"""
    {cte},
    order_totals AS (
        SELECT order_id, SUM(payment_value) AS order_total
        FROM payments
        GROUP BY order_id
    )
    SELECT
        SUM(ot.order_total)                      AS total_revenue,
        COUNT(DISTINCT fo.order_id)              AS total_orders,
        AVG(ot.order_total)                      AS avg_order_value,
        ROUND(AVG(r.review_score)::numeric, 2)   AS avg_review_score
    FROM filtered_orders fo
    JOIN order_totals ot ON fo.order_id = ot.order_id
    LEFT JOIN reviews r  ON fo.order_id = r.order_id
    """


def monthly_revenue_query(start, end, states, categories):
    cte = _filtered_orders_cte(start, end, states, categories)
    return f"""
    {cte},
    monthly AS (
        SELECT
            date_trunc('month', fo.order_purchase_timestamp)::date AS month,
            SUM(p.payment_value)               AS total_revenue,
            COUNT(DISTINCT fo.order_id)        AS total_orders
        FROM filtered_orders fo
        JOIN payments p ON fo.order_id = p.order_id
        WHERE fo.order_status != 'canceled'
        GROUP BY 1
    )
    SELECT
        month,
        total_revenue,
        total_orders,
        ROUND(
            (total_revenue - LAG(total_revenue) OVER (ORDER BY month))
            / NULLIF(LAG(total_revenue) OVER (ORDER BY month), 0) * 100,
            2
        ) AS mom_growth_pct
    FROM monthly
    ORDER BY month
    """


def order_status_query(start, end, states, categories):
    cte = _filtered_orders_cte(start, end, states, categories)
    return f"""
    {cte}
    SELECT
        fo.order_status,
        COUNT(*) AS order_count
    FROM filtered_orders fo
    GROUP BY 1
    ORDER BY 2 DESC
    """


def revenue_by_category_query(start, end, states, categories):
    cte = _filtered_orders_cte(start, end, states, categories)
    return f"""
    {cte}
    SELECT
        COALESCE(pr.product_category_name, 'Unknown') AS category,
        SUM(oi.price)                                  AS total_revenue,
        COUNT(DISTINCT fo.order_id)                    AS total_orders
    FROM filtered_orders fo
    JOIN order_items oi ON fo.order_id   = oi.order_id
    JOIN products pr    ON oi.product_id = pr.product_id
    GROUP BY 1
    ORDER BY total_revenue DESC
    LIMIT 15
    """


def revenue_by_state_query(start, end, states, categories):
    cte = _filtered_orders_cte(start, end, states, categories)
    return f"""
    {cte},
    order_totals AS (
        SELECT order_id, SUM(payment_value) AS order_total
        FROM payments
        GROUP BY order_id
    )
    SELECT
        c.customer_state            AS state,
        SUM(ot.order_total)         AS total_revenue,
        COUNT(DISTINCT fo.order_id) AS total_orders
    FROM filtered_orders fo
    JOIN customers c     ON fo.customer_id = c.customer_id
    JOIN order_totals ot ON fo.order_id    = ot.order_id
    GROUP BY 1
    ORDER BY total_revenue DESC
    LIMIT 20
    """


def top_sellers_query(start, end, states, categories):
    cte = _filtered_orders_cte(start, end, states, categories)
    return f"""
    {cte}
    SELECT
        s.seller_id,
        s.seller_city,
        s.seller_state,
        SUM(oi.price + oi.shipping_charges)    AS total_revenue,
        COUNT(DISTINCT fo.order_id)             AS orders_fulfilled,
        ROUND(AVG(r.review_score)::numeric, 2) AS avg_review_score
    FROM filtered_orders fo
    JOIN order_items oi ON fo.order_id  = oi.order_id
    JOIN sellers s      ON oi.seller_id = s.seller_id
    LEFT JOIN reviews r ON fo.order_id  = r.order_id
    GROUP BY 1, 2, 3
    ORDER BY total_revenue DESC
    LIMIT 10
    """


def payment_type_query(start, end, states, categories):
    cte = _filtered_orders_cte(start, end, states, categories)
    return f"""
    {cte}
    SELECT
        p.payment_type,
        COUNT(DISTINCT fo.order_id) AS total_orders,
        SUM(p.payment_value)        AS total_revenue
    FROM filtered_orders fo
    JOIN payments p ON fo.order_id = p.order_id
    GROUP BY 1
    ORDER BY total_revenue DESC
    """
