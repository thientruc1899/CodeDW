CREATE SCHEMA IF NOT EXISTS staging;

-- =====================================================
-- RAW: append-only, order_id có thể duplicate
-- PostgreSQL
-- =====================================================

CREATE TABLE IF NOT EXISTS staging.stg_inform_ecom_order_detail (
    id VARCHAR(36) NOT NULL,
    parent_id VARCHAR(36) NULL,
    order_id VARCHAR(50) NOT NULL,

    code VARCHAR(20) NULL,
    old_sku VARCHAR(255) NOT NULL,
    new_sku VARCHAR(255) NULL,
    name VARCHAR(255) NULL,

    origin_price NUMERIC(9,2) NULL,
    paid_price NUMERIC(9,2) NOT NULL DEFAULT 0.00,
    net_price NUMERIC(9,2) NOT NULL DEFAULT 0.00,

    quan SMALLINT NOT NULL DEFAULT 1,
    refund_quan SMALLINT NOT NULL DEFAULT 0,
    cb_quan SMALLINT NOT NULL DEFAULT 0,

    canceled SMALLINT NOT NULL DEFAULT 0,

    barcode VARCHAR(500) NULL,
    item_id VARCHAR(255) NULL,

    manual SMALLINT NOT NULL DEFAULT 0,

    pos VARCHAR(50) NULL,

    product_variant_id BIGINT NULL,

    wh_code VARCHAR(50) NULL,

    created_at TIMESTAMP NULL,

    CONSTRAINT pk_stg_inform_ecom_order_detail
        PRIMARY KEY (id)
);

-- Index phục vụ join / delete / filter theo order_id
CREATE INDEX IF NOT EXISTS idx_stg_inform_ecom_order_detail_order_id
    ON staging.stg_inform_ecom_order_detail (order_id);