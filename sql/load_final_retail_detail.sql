-- staging.stg_inform_retail_order_detail -> staging.final_inform_retail_order_detail
--
-- Bảng detail KHÔNG có id -> không upsert từng dòng được.
-- Cách làm: đơn nào có trong batch mới thì XOÁ toàn bộ dòng cũ của đơn đó trong final,
-- rồi CHÈN lại toàn bộ dòng của lần kéo mới nhất (loaded_at lớn nhất) của đơn đó.
--
-- Yêu cầu (chạy tay 1 lần):
--   CREATE INDEX IF NOT EXISTS idx_final_inform_retail_order_detail_order_id
--       ON staging.final_inform_retail_order_detail (order_id);
--   CREATE INDEX IF NOT EXISTS idx_stg_inform_retail_order_detail_loaded_at
--       ON staging.stg_inform_retail_order_detail (loaded_at);

WITH wm AS (
    SELECT COALESCE(MAX(loaded_at), '-infinity'::timestamp) AS last_loaded
    FROM staging.final_inform_retail_order_detail
),
latest AS (
    -- mỗi đơn chỉ lấy lần kéo mới nhất
    SELECT
        s.order_id,
        MAX(s.loaded_at) AS loaded_at
    FROM staging.stg_inform_retail_order_detail s
    CROSS JOIN wm
    WHERE s.loaded_at > wm.last_loaded
    GROUP BY s.order_id
),
del AS (
    -- xoá dòng cũ của các đơn có thay đổi
    DELETE FROM staging.final_inform_retail_order_detail f
    USING latest l
    WHERE f.order_id = l.order_id
)
INSERT INTO staging.final_inform_retail_order_detail (
    order_id,
    parent_code,
    old,
    name,
    quan,
    refund_quan,
    paid_price,
    origin_price,
    total_price,
    barcode,
    pro_id,
    variant_id,
    product_variant_id,
    promotion_id,
    promotion_name,
    created_at,
    loaded_at
)
SELECT
    s.order_id,
    s.parent_code,
    s.old,
    s.name,
    s.quan,
    s.refund_quan,
    s.paid_price,
    s.origin_price,
    s.total_price,
    s.barcode,
    s.pro_id,
    s.variant_id,
    s.product_variant_id,
    s.promotion_id,
    s.promotion_name,
    s.created_at,
    s.loaded_at
FROM staging.stg_inform_retail_order_detail s
INNER JOIN latest l
    ON  s.order_id  = l.order_id
    AND s.loaded_at = l.loaded_at;