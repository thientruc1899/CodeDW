CREATE SCHEMA IF NOT EXISTS staging;

-- Raw, append-only (duplicates OK)
CREATE TABLE IF NOT EXISTS staging.stg_inform_ecom_order_line (
    "id"                    integer,
    "order_id"              integer,
    "order_name"            text,
    "order_date"            timestamp,
    "completed_date"        timestamp,
    "order_status"          smallint,
    "type_lv2"              text,
    "type_lv1"              text,
    "origin_customer_id"    text,
    "customer_id"           text,
    "customer_info"         text,
    "sale_man"              text,
    "location_hrv_id"       text,
    "location_name"         text,
    "channel_id"            integer,
    "model_sku"             text,
    "variant_id"            text,
    "barcode"               text,
    "promotion_name"        text,
    "partner_discount"      numeric,
    "vat_contract"          numeric,
    "vat_current"           numeric,
    "qty_ordered"           integer,
    "qty_delivered"         integer,
    "gross_revenue"         numeric,
    "net_revenue_bf_coupon" numeric,
    "net_revenue"           numeric,
    "net_revenue_actual"    numeric,
    "coupon_amount"         numeric,
    "note"                  text,
    "warehouse_id"          integer,
    "warehouse_name"        text,
    "warehouse_status"      smallint,
    "warehouse_date"        timestamp,
    "return_name"           text,
    "data_source"           text,
    "updated_at"            timestamp
);

-- Final: 1 row per line id, same columns
CREATE TABLE IF NOT EXISTS staging.stg_ecom_order_line_final
    (LIKE staging.stg_inform_ecom_order_line);

-- Index cho bước delete theo order_id mỗi ngày
CREATE INDEX IF NOT EXISTS idx_stg_ecom_order_line_final_order_id
    ON staging.stg_ecom_order_line_final ("order_id");
CREATE INDEX IF NOT EXISTS idx_stg_ecom_order_line_final_id
    ON staging.stg_ecom_order_line_final ("id");