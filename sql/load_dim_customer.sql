-- =====================================================
-- STAGING -> public.dim_customer (SCD2: level, full_name, phone)
-- Watermark = max(src_loaded_at) trong dim
-- =====================================================

-- -----------------------------------------------------
-- 0. Gom batch mới + chuẩn hoá vào bảng tạm
-- -----------------------------------------------------
DROP TABLE IF EXISTS tmp_customer;

CREATE TEMP TABLE tmp_customer AS
WITH latest AS (
    SELECT DISTINCT ON (s.id) s.*
    FROM staging.stg_inform_customer s
    WHERE s.loaded_at > COALESCE(
        (SELECT MAX(src_loaded_at) FROM public.dim_customer),
        '1900-01-01'::TIMESTAMPTZ
    )
    ORDER BY s.id, s.loaded_at DESC
),
digits AS (
    SELECT
        l.*,
        NULLIF(REGEXP_REPLACE(COALESCE(l.phone, ''), '[^0-9]', '', 'g'), '') AS p0
    FROM latest l
),
norm AS (
    SELECT
        d.*,
        CASE
            WHEN d.p0 IS NULL THEN NULL
            WHEN LENGTH(d.p0) = 9  AND LEFT(d.p0, 1) IN ('3','5','7','8','9') THEN '0' || d.p0
            WHEN LENGTH(d.p0) = 11 AND LEFT(d.p0, 2) = '84'                   THEN '0' || SUBSTR(d.p0, 3)
            WHEN LENGTH(d.p0) = 12 AND LEFT(d.p0, 3) = '084'                  THEN '0' || SUBSTR(d.p0, 4)
            WHEN LENGTH(d.p0) = 13 AND LEFT(d.p0, 4) = '0840'                 THEN SUBSTR(d.p0, 4)
            WHEN LENGTH(d.p0) = 11 AND m.new_head IS NOT NULL                 THEN m.new_head || SUBSTR(d.p0, 5)
            ELSE d.p0
        END AS phone_norm
    FROM digits d
    LEFT JOIN staging.map_phone_prefix m
        ON m.old_head = LEFT(d.p0, 4)
)
SELECT
    n.id                                AS inform_id,
    n.hrv_id,
    -- SCD2
    NULLIF(TRIM(n.level), '')           AS level,
    NULLIF(TRIM(n.full_name), '')       AS full_name,
    n.phone_norm                        AS phone,
    CASE WHEN n.phone_norm ~ '^0[35789][0-9]{8}$'
          AND n.phone_norm NOT LIKE '%00000000%'
         THEN 1 ELSE 0 END              AS is_valid_phone,
    -- thời điểm thay đổi
    COALESCE(n.updated_at, n.loaded_at::TIMESTAMP) AS change_ts,
    -- SCD1
    n.phone                             AS inform_phone,
    NULLIF(LOWER(TRIM(n.email)), '')    AS email,
    public.try_date(n.birthday)             AS birthday,
    CASE WHEN public.try_date(n.birthday) IS NULL THEN 0 ELSE 1 END AS is_dob,
    n.gender,
    n.total_point,
    n.total_purchase,
    n.street, n.ward, n.district, n.province,
    n.last_online_order,
    n.last_offline_order,
    n.last_date_order                   AS last_order_date,
    n.last_online_date,
    n.last_offline_date,
    n.created_at,
    n.updated_at,
    n.loaded_at                        AS src_loaded_at
FROM norm n;


-- -----------------------------------------------------
-- 1. Đóng dòng hiện hành nếu level / full_name / phone đổi
-- -----------------------------------------------------
UPDATE public.dim_customer d
SET valid_to      = GREATEST(t.change_ts, d.valid_from),
    is_current    = 0,
    dw_updated_at = now()
FROM tmp_customer t
WHERE d.inform_id  = t.inform_id
  AND d.is_current = 1
  AND (   d.level     IS DISTINCT FROM t.level
       OR d.full_name IS DISTINCT FROM t.full_name
       OR d.phone     IS DISTINCT FROM t.phone);


-- -----------------------------------------------------
-- 2. Thêm dòng mới: khách mới + khách vừa bị đóng dòng
--    Khách mới: valid_from = 1900-01-01 để fact cũ vẫn join được
--    Khách đổi: valid_from = valid_to của dòng vừa đóng
-- -----------------------------------------------------
INSERT INTO public.dim_customer (
    inform_id, hrv_id,
    level, full_name, phone, is_valid_phone,
    valid_from, valid_to, is_current,
    inform_phone, email, birthday, is_dob, gender,
    total_point, total_purchase,
    street, ward, district, province,
    last_online_order, last_offline_order, last_order_date,
    last_online_date, last_offline_date,
    created_at,
    src_loaded_at
)
SELECT
    t.inform_id, t.hrv_id,
    t.level, t.full_name, t.phone, t.is_valid_phone,
    COALESCE(
        (SELECT MAX(x.valid_to) FROM public.dim_customer x WHERE x.inform_id = t.inform_id),
        '1900-01-01'::TIMESTAMP
    ),
    '9999-12-31'::TIMESTAMP,
    1,
    t.inform_phone, t.email, t.birthday, t.is_dob, t.gender,
    t.total_point, t.total_purchase,
    t.street, t.ward, t.district, t.province,
    t.last_online_order, t.last_offline_order, t.last_order_date,
    t.last_online_date, t.last_offline_date,
    t.created_at,
    t.src_loaded_at
FROM tmp_customer t
WHERE NOT EXISTS (
    SELECT 1 FROM public.dim_customer d
    WHERE d.inform_id = t.inform_id AND d.is_current = 1
);


-- -----------------------------------------------------
-- 3. SCD1: ghi đè các cột còn lại trên dòng hiện hành
-- -----------------------------------------------------
UPDATE public.dim_customer d
SET hrv_id             = t.hrv_id,
    inform_phone       = t.inform_phone,
    email              = t.email,
    birthday           = t.birthday,
    is_dob             = t.is_dob,
    gender             = t.gender,
    total_point        = t.total_point,
    total_purchase     = t.total_purchase,
    street             = t.street,
    ward               = t.ward,
    district           = t.district,
    province           = t.province,
    last_online_order  = t.last_online_order,
    last_offline_order = t.last_offline_order,
    last_order_date    = t.last_order_date,
    last_online_date   = t.last_online_date,
    last_offline_date  = t.last_offline_date,
    created_at         = t.created_at,
    src_loaded_at      = t.src_loaded_at
FROM tmp_customer t
WHERE d.inform_id  = t.inform_id
  AND d.is_current = 1;


-- -----------------------------------------------------
-- 4. is_primary_phone: chỉ xét dòng hiện hành
-- -----------------------------------------------------
WITH ranked AS (
    SELECT
        customer_key,
        CASE WHEN ROW_NUMBER() OVER (
            PARTITION BY phone
            ORDER BY last_order_date DESC NULLS LAST,
                     created_at      DESC NULLS LAST,
                     inform_id       DESC
        ) = 1 THEN 1 ELSE 0 END AS flag
    FROM public.dim_customer
    WHERE is_current = 1 AND is_valid_phone = 1
)
UPDATE public.dim_customer d
SET is_primary_phone = r.flag
FROM ranked r
WHERE d.customer_key = r.customer_key
  AND d.is_primary_phone IS DISTINCT FROM r.flag;

UPDATE public.dim_customer
SET is_primary_phone = 0
WHERE (is_current = 0 OR is_valid_phone = 0)
  AND is_primary_phone IS DISTINCT FROM 0;

DROP TABLE IF EXISTS tmp_customer;
