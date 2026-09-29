CREATE TABLE staging.stg_inform_ecom_order_detail (
    id VARCHAR(36) NOT NULL,
    parent_id VARCHAR(36),
    order_id VARCHAR(50) NOT NULL,
    code VARCHAR(20),
    old_sku VARCHAR(255) NOT NULL,
    new_sku VARCHAR(255),
    name VARCHAR(255),
    origin_price NUMERIC(9,2),
    paid_price NUMERIC(9,2) NOT NULL DEFAULT 0.00,
    net_price NUMERIC(9,2) NOT NULL DEFAULT 0.00,
    quan SMALLINT NOT NULL DEFAULT 1,
    refund_quan SMALLINT NOT NULL DEFAULT 0,
    cb_quan SMALLINT NOT NULL DEFAULT 0,
    canceled SMALLINT NOT NULL DEFAULT 0,
    barcode VARCHAR(500),
    item_id VARCHAR(255),
    manual SMALLINT NOT NULL DEFAULT 0,
    pos VARCHAR(50),
    product_variant_id BIGINT,
    wh_code VARCHAR(50),
    created_at TIMESTAMP,

    -- ETL metadata
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- Index by ID
CREATE INDEX idx_stg_inform_ecom_order_detail_id
ON staging.stg_inform_ecom_order_detail (id);


-- Index JOIN với order
CREATE INDEX idx_stg_inform_ecom_order_detail_order_id
ON staging.stg_inform_ecom_order_detail (order_id);


-- Index snapshot mới nhất
CREATE INDEX idx_stg_inform_ecom_order_detail_loaded_at
ON staging.stg_inform_ecom_order_detail (loaded_at);