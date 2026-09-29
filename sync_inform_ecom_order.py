from datetime import date, timedelta

from helper.class_resource import Resource


DEST_SCHEMA = "staging"

target_date = date.today() - timedelta(days=1)

print(f"Pulling data for date: {target_date}")


# ==============================
# SQL ECOM ORDER
# ==============================

sql_order = """
    SELECT *
    FROM ecom_order
    WHERE DATE(COALESCE(updated_at, created_at)) = %s
"""


# ==============================
# SQL ECOM ORDER DETAIL
# ==============================

sql_order_detail = """
    SELECT d.*
    FROM ecom_order o
    INNER JOIN ecom_order_detail d ON o.order_id = d.order_id
    WHERE DATE(COALESCE(o.updated_at, o.created_at)) = %s
"""


# ==============================
# CONNECT
# ==============================

resource = Resource()

try:

    resource.connect()


    # ==========================
    # 1. ECOM ORDER
    # ==========================

    print("\nSyncing ecom_order...")

    rows_order = resource.pull_by_date(
        sql_order,
        target_date
    )

    resource.insert_postgres(
        rows_order,
        DEST_SCHEMA,
        "stg_inform_ecom_order"
    )


    # ==========================
    # 2. ECOM ORDER DETAIL
    # ==========================

    print("\nSyncing ecom_order_detail...")

    rows_detail = resource.pull_by_date(
        sql_order_detail,
        target_date
    )

    resource.insert_postgres(
        rows_detail,
        DEST_SCHEMA,
        "stg_inform_ecom_order_detail"
    )


finally:

    resource.close()