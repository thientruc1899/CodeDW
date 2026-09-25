SELECT b.id,a.id AS order_id,
a.order_id AS order_name,

a.created_at AS order_date,
a.delivery_at AS completed_date,
a.status AS order_status, 
case
  when UPPER(a.customer_note) LIKE '%THU COD%' then 'Sale - Exchange'
  ELSE 'Sale - Sale' end AS type_lv2,
'Sale'  AS type_lv1,
a.customer_id AS origin_customer_id,
a.customer_name AS customer_id,
'No' AS customer_info,
a.uic_name AS sale_man,
'' as location_hrv_id,
a.channel  as location_name,
case 
        when a.channel like 'Shopee%' then 50001
  when a.channel IN ( 'Shopee2') then 50004
  when a.channel IN ('Lazada') then 50002
  when a.channel IN ('Lazada2') then 50005
  when a.channel IN ('Tiki') then 50003
  when a.channel IN ('Tiktok', 'Tiktok2') then 60001
  ELSE 00000 END AS channel_id,
b.old_sku as model_sku,
c.product_variant_id as variant_id ,
c.barcode,
'' AS promotion_name,
0 AS partner_discount,
0.08 AS vat_contract,
0.08 AS vat_current,
(c.quan - c.canceled) AS qty_ordered, 
(c.quan - c.canceled) AS qty_delivered, 
(c.quan - c.canceled)*c.origin_price AS gross_revenue, 
(c.quan - c.canceled)*c.paid_price AS net_revenue_bf_coupon, 
(c.quan - c.canceled)*c.paid_price AS net_revenue, 
(c.quan - c.canceled)*c.net_price AS net_revenue_actual, 
0 AS coupon_amount,
a.customer_note AS note,
a.location_id AS warehouse_id, 
a.picking_name as warehouse_name,
a.picking_status AS warehouse_status,
a.delivery_at AS warehouse_date, 
'' AS return_name,
'ecom_order_inform' AS data_source,
a.updated_at
FROM ecom_order a
  INNER JOIN ecom_order_detail  b ON a.order_id = b.order_id
  INNER JOIN ecom_order_detail c ON b.id = c.parent_id
WHERE ( a.created_at >= NOW() - INTERVAL 5 DAY
 or a.updated_at >= NOW() - INTERVAL 5 DAY )
AND c.id IS NOT NULL
AND c.canceled = 0 
AND a.status NOT IN(-1)