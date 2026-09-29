CREATE TABLE staging.stg_inform_ecom_order (
    id BIGINT NOT NULL,
    order_id VARCHAR(50) NOT NULL,
    rso_name VARCHAR(50),
    channel VARCHAR(20) NOT NULL,
    customer_id VARCHAR(50),
    customer_name VARCHAR(100),
    order_flag VARCHAR(30),
    deadline TIMESTAMP,
    delivery_at TIMESTAMP,
    fulfillment_at TIMESTAMP,
    complete_at TIMESTAMP,
    cancel_at TIMESTAMP,
    status SMALLINT NOT NULL DEFAULT 0,
    ps_status VARCHAR(150),
    picking_status SMALLINT,
    picking_name VARCHAR(50),
    total_items INTEGER NOT NULL DEFAULT 0,
    total_amount NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    net_price NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    address_shipping VARCHAR(255) NOT NULL,
    phone_shipping VARCHAR(100) NOT NULL,
    customer_note VARCHAR(500),
    packing_note VARCHAR(500),
    repick_stt SMALLINT,
    repick_note TEXT,
    shipping_carrier VARCHAR(255),
    cron_handle_detail VARCHAR(20) NOT NULL DEFAULT 'uncheck',
    uic_id INTEGER,
    uic_name VARCHAR(255),
    get_by VARCHAR(255) NOT NULL,
    warehouse VARCHAR(50) NOT NULL DEFAULT 'WH-PS',
    location_id INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP,
    updated_id INTEGER,
    package_code VARCHAR(50),

    -- ETL metadata
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stg_inform_ecom_order_id
ON staging.stg_inform_ecom_order (id);

CREATE INDEX idx_stg_inform_ecom_order_order_id
ON staging.stg_inform_ecom_order (order_id);

CREATE INDEX idx_stg_inform_ecom_order_updated_at
ON staging.stg_inform_ecom_order (updated_at);

CREATE INDEX idx_stg_inform_ecom_order_loaded_at
ON staging.stg_inform_ecom_order (loaded_at);