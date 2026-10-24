-- staging.stg_inform_retail_order -> staging.final_inform_retail_order
-- Yêu cầu (chạy tay 1 lần):
--   ALTER TABLE staging.final_inform_retail_order ADD PRIMARY KEY (order_id);
--   CREATE INDEX IF NOT EXISTS idx_stg_inform_retail_order_loaded_at
--       ON staging.stg_inform_retail_order (loaded_at);

WITH wm AS (
    SELECT COALESCE(MAX(loaded_at), '-infinity'::timestamp) AS last_loaded
    FROM staging.final_inform_retail_order
),
batch AS (
    SELECT
        s.*,
        ROW_NUMBER() OVER (
            PARTITION BY s.order_id
            ORDER BY
                COALESCE(s.updated_at, s.created_at) DESC NULLS LAST,
                s.loaded_at DESC
        ) AS rn
    FROM staging.stg_inform_retail_order s
    CROSS JOIN wm
    WHERE s.loaded_at > wm.last_loaded
)
INSERT INTO staging.final_inform_retail_order AS f (
    order_id,
    order_name,
    odoo_so,
    location_name,
    customer_name,
    customer_id,
    status,
    total_item,
    total_price,
    subtotal_price,
    email,
    total_discount,
    phone,
    note,
    date_create_order,
    ref_order_id,
    location_id,
    location_stock,
    created_at,
    created_id,
    updated_at,
    get_by,
    cancel_token,
    cancel_note,
    member_request_id,
    e_invoice,
    stock_status,
    loaded_at
)
SELECT
    order_id,
    order_name,
    odoo_so,
    location_name,
    customer_name,
    customer_id,
    status,
    total_item,
    total_price,
    subtotal_price,
    email,
    total_discount,
    phone,
    note,
    date_create_order,
    ref_order_id,
    location_id,
    location_stock,
    created_at,
    created_id,
    updated_at,
    get_by,
    cancel_token,
    cancel_note,
    member_request_id,
    e_invoice,
    stock_status,
    loaded_at
FROM batch
WHERE rn = 1
ON CONFLICT (order_id) DO UPDATE SET
    order_name         = EXCLUDED.order_name,
    odoo_so            = EXCLUDED.odoo_so,
    location_name      = EXCLUDED.location_name,
    customer_name      = EXCLUDED.customer_name,
    customer_id        = EXCLUDED.customer_id,
    status             = EXCLUDED.status,
    total_item         = EXCLUDED.total_item,
    total_price        = EXCLUDED.total_price,
    subtotal_price     = EXCLUDED.subtotal_price,
    email              = EXCLUDED.email,
    total_discount     = EXCLUDED.total_discount,
    phone              = EXCLUDED.phone,
    note               = EXCLUDED.note,
    date_create_order  = EXCLUDED.date_create_order,
    ref_order_id       = EXCLUDED.ref_order_id,
    location_id        = EXCLUDED.location_id,
    location_stock     = EXCLUDED.location_stock,
    created_at         = EXCLUDED.created_at,
    created_id         = EXCLUDED.created_id,
    updated_at         = EXCLUDED.updated_at,
    get_by             = EXCLUDED.get_by,
    cancel_token       = EXCLUDED.cancel_token,
    cancel_note        = EXCLUDED.cancel_note,
    member_request_id  = EXCLUDED.member_request_id,
    e_invoice          = EXCLUDED.e_invoice,
    stock_status       = EXCLUDED.stock_status,
    loaded_at          = EXCLUDED.loaded_at
WHERE COALESCE(EXCLUDED.updated_at, EXCLUDED.created_at, '-infinity'::timestamp)
   >= COALESCE(f.updated_at, f.created_at, '-infinity'::timestamp);