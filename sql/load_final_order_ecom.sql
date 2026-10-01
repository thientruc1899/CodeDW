WITH changed_ids AS (
    SELECT DISTINCT id
    FROM staging.stg_inform_ecom_order
    WHERE loaded_at >= CURRENT_DATE - INTERVAL '2 days'
),
ranked AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY r.id
            ORDER BY
                r.loaded_at DESC,
                r.ctid DESC
        ) AS rn
    FROM staging.stg_inform_ecom_order r
    INNER JOIN changed_ids c
        ON r.id = c.id
)
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
FROM ranked
WHERE rn = 1;