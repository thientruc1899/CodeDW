
-- CREATE INDEX IF NOT EXISTS ix_stg_ecom_order_loaded_at
--     ON staging.stg_inform_ecom_order (loaded_at);
--
-- CREATE INDEX IF NOT EXISTS ix_stg_ecom_order_id
--     ON staging.stg_inform_ecom_order (id);
--
-- CREATE UNIQUE INDEX IF NOT EXISTS ux_final_ecom_order_id
--     ON staging.final_inform_ecom_order (id);
-- ------------------------------------------------------------
CREATE TEMP TABLE tmp_changed_ecom_order_ids
ON COMMIT DROP
AS
SELECT DISTINCT id
FROM staging.stg_inform_ecom_order
WHERE loaded_at >= CURRENT_DATE - INTERVAL '2 days';

-- Temp table mới tạo chưa có thống kê -> planner đoán sai, join rất chậm.
ANALYZE tmp_changed_ecom_order_ids;

INSERT INTO staging.final_inform_ecom_order (
    id,
    order_id,
    rso_name,
    channel,
    customer_id,
    customer_name,
    order_flag,
    deadline,
    delivery_at,
    fulfillment_at,
    complete_at,
    cancel_at,
    status,
    ps_status,
    picking_status,
    picking_name,
    total_items,
    total_amount,
    net_price,
    address_shipping,
    phone_shipping,
    customer_note,
    packing_note,
    repick_stt,
    repick_note,
    shipping_carrier,
    cron_handle_detail,
    uic_id,
    uic_name,
    get_by,
    warehouse,
    location_id,
    created_at,
    updated_at,
    updated_id,
    package_code,
    loaded_at
)
SELECT
    id,
    order_id,
    rso_name,
    channel,
    customer_id,
    customer_name,
    order_flag,
    deadline,
    delivery_at,
    fulfillment_at,
    complete_at,
    cancel_at,
    status,
    ps_status,
    picking_status,
    picking_name,
    total_items,
    total_amount,
    net_price,
    address_shipping,
    phone_shipping,
    customer_note,
    packing_note,
    repick_stt,
    repick_note,
    shipping_carrier,
    cron_handle_detail,
    uic_id,
    uic_name,
    get_by,
    warehouse,
    location_id,
    created_at,
    updated_at,
    updated_id,
    package_code,
    loaded_at
FROM (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY r.id
            ORDER BY
                r.loaded_at DESC,
                r.ctid      DESC
        ) AS rn
    FROM staging.stg_inform_ecom_order r
    INNER JOIN tmp_changed_ecom_order_ids c
        ON r.id = c.id
) ranked
WHERE rn = 1;


