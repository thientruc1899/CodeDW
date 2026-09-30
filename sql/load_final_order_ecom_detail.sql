CREATE TEMP TABLE tmp_changed_ecom_order_detail_ids
ON COMMIT DROP
AS
SELECT DISTINCT id
FROM staging.stg_inform_ecom_order_detail
WHERE loaded_at >= CURRENT_DATE - INTERVAL '2 days';

-- Temp table mới tạo chưa có thống kê -> planner đoán sai, join rất chậm.
ANALYZE tmp_changed_ecom_order_detail_ids;

-- 3. Ghi lại bản mới nhất của từng id.
--    Xét toàn bộ lịch sử staging của id đó (không chỉ 2 ngày) để chắc chắn
--    lấy đúng bản mới nhất.
INSERT INTO staging.final_inform_ecom_order_detail (
    id,
    parent_id,
    order_id,
    code,
    old_sku,
    new_sku ,
    name ,
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
    new_sku ,
    name ,
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
            PARTITION BY r.id
            ORDER BY
                r.loaded_at DESC,
                r.ctid      DESC
        ) AS rn
    FROM staging.stg_inform_ecom_order_detail r
    INNER JOIN tmp_changed_ecom_order_detail_ids c
        ON r.id = c.id
) ranked
WHERE rn = 1;