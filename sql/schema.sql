-- CUSTOMERS


CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    customer_zip_code_prefix INT NOT NULL,
    customer_city TEXT NOT NULL,
    customer_state TEXT NOT NULL
);



-- ORDERS


CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    order_status TEXT NOT NULL,
    order_purchase_timestamp TIMESTAMPTZ NOT NULL,
    order_delivered_timestamp TIMESTAMPTZ,

    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);



-- PRODUCTS


CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    product_category_name TEXT,
    product_weight DECIMAL,
    product_length DECIMAL,
    product_height DECIMAL
);



-- SELLERS


CREATE TABLE sellers (
    seller_id TEXT PRIMARY KEY,
    seller_zip_code_prefix INT NOT NULL,
    seller_city TEXT NOT NULL,
    seller_state TEXT NOT NULL
);



-- ORDER ITEMS (Bridge Table)


CREATE TABLE order_items (
    order_id TEXT NOT NULL,
    order_item_id INT NOT NULL,
    product_id TEXT NOT NULL,
    seller_id TEXT NOT NULL,
    price DECIMAL NOT NULL,
    shipping_charges DECIMAL NOT NULL,

    PRIMARY KEY (order_id, order_item_id),

    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
);



-- PAYMENTS

CREATE TABLE payments (
    order_id TEXT NOT NULL,
    payment_sequential INT NOT NULL,
    payment_type TEXT NOT NULL,
    payment_installments INT,
    payment_value DECIMAL NOT NULL CHECK (payment_value >= 0),

    PRIMARY KEY (order_id, payment_sequential),

    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);



-- REVIEWS

CREATE TABLE reviews (
    review_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    review_score INT NOT NULL CHECK (review_score BETWEEN 1 AND 5),
    review_comment TEXT,

    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);