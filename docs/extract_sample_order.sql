SELECT *
FROM ecom_order a
WHERE (
    DATE(a.created_at) = %s
    OR DATE(a.updated_at) = %s
)


SELECT b.*
FROM ecom_order a
INNER JOIN ecom_order_detail  b ON a.order_id = b.order_id
WHERE (
    DATE(COALESCE(a.updated_at, a.created_at)) = %s
)



CREATE TABLE staging.final_inform_ecom_order_detail AS
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
FROM (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY id
            ORDER BY loaded_at DESC
        ) AS rn
    FROM staging.stg_inform_ecom_order_detail r
) ranked
WHERE rn = 1;