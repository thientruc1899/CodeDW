SELECT b.*
FROM ecom_order a
INNER JOIN ecom_order_detail  b ON a.order_id = b.order_id
WHERE (
    DATE(a.created_at) = %s
    OR DATE(a.updated_at) = %s
)
