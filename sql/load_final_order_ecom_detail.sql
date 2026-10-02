WITH changed_ids AS (
    SELECT DISTINCT id
    FROM staging.stg_inform_ecom_order_detail
    WHERE loaded_at >= CURRENT_DATE - INTERVAL '1 days'
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
    FROM staging.stg_inform_ecom_order_detail r
    INNER JOIN changed_ids c
        ON r.id = c.id
)

INSERT INTO staging.final_inform_ecom_order_detail (
    id,
    parent_id,
    order_id,
    code,
    old_sku,
    new_sku,
    name,
    origin_price,
    paid_price,
    net_price,
    quan,
    refund_quan,
    cb_quan,
    canceled,
    barcode,
    item_id,
    manual,
    pos,
    product_variant_id,
    wh_code,
    created_at,
    loaded_at
)
SELECT
    id,
    parent_id,
    order_id,
    code,
    old_sku,
    new_sku,
    name,
    origin_price,
    paid_price,
    net_price,
    quan,
    refund_quan,
    cb_quan,
    canceled,
    barcode,
    item_id,
    manual,
    pos,
    product_variant_id,
    wh_code,
    created_at,
    loaded_at
FROM ranked
WHERE rn = 1;