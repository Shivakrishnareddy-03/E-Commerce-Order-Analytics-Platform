-- ============================================================
-- STRATEGIC INDEXES for Performance Optimization
-- ============================================================

-- Speed up joins on orders.customer_id (used in most analytical queries)
CREATE INDEX IF NOT EXISTS idx_orders_customer_id
    ON orders (customer_id);

-- Speed up time-based aggregations (Query 1 & 3)
CREATE INDEX IF NOT EXISTS idx_orders_purchase_timestamp
    ON orders (order_purchase_timestamp);

-- Speed up seller joins in Query 2 and fact table builds
CREATE INDEX IF NOT EXISTS idx_order_items_seller_id
    ON order_items (seller_id);

-- Speed up order-level joins on order_items
CREATE INDEX IF NOT EXISTS idx_order_items_order_id
    ON order_items (order_id);

-- Speed up payment aggregations by order
CREATE INDEX IF NOT EXISTS idx_payments_order_id
    ON payments (order_id);

-- Speed up review lookups by order
CREATE INDEX IF NOT EXISTS idx_reviews_order_id
    ON reviews (order_id);

-- Filtered index for non-canceled orders (Query 1)
CREATE INDEX IF NOT EXISTS idx_orders_status_not_canceled
    ON orders (order_purchase_timestamp)
    WHERE order_status != 'canceled';
