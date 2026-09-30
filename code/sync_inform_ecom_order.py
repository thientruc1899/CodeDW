"""
Job: Inform (MariaDB) -> staging.stg_inform_ecom_order -> staging.final_inform_ecom_order

Run:    
    python code/sync_ecom_order.py
"""

import sys
from pathlib import Path
from datetime import date, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SQL_DIR = PROJECT_ROOT / "sql"

from helper.class_resource import Resource





DEST_SCHEMA = "staging"
DEST_TABLE = "stg_inform_ecom_order"


target_date = date.today() - timedelta(days=1)
# ==============================
# SQL
# ==============================

COLUMNS = """
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
    package_code
"""

SQL_ORDER = f"""
    SELECT {COLUMNS}
    FROM ecom_order
    WHERE DATE(COALESCE(updated_at, created_at)) = %s
"""


# ==============================
# RUN
# ==============================

print(f"Pulling data for date: {target_date}")


resource = Resource()
 
try:
 
    resource.connect()
 
    print("\nSyncing ecom_order...")
 
    rows_order = resource.pull_by_date(
        SQL_ORDER,
        target_date
    )
 
    resource.insert_postgres(
        rows_order,
        DEST_SCHEMA,
        "stg_inform_ecom_order"
    )
 
    resource.execute_postgres_sql(
        SQL_DIR / "load_final_order_ecom.sql"
    )
 
finally:
    resource.close()

