import sys
from pathlib import Path
from datetime import date

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SQL_DIR = PROJECT_ROOT / "sql"

from helper.class_resource_range_date import Resource


DEST_SCHEMA = "staging"
DEST_TABLE = "stg_inform_ecom_order"


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
SELECT
    {COLUMNS}
FROM ecom_order
WHERE created_at >= %s
  AND created_at < %s
"""

start_date = date(2026, 9, 1)
end_date = date(2026, 10, 1)



resource = Resource()

try:
    resource.connect()

    print("Syncing ecom_order for 2026-09...")

    rows_order = resource.pull_by_params(SQL_ORDER,  (start_date, end_date) )

    resource.insert_postgres(
        rows_order,
        DEST_SCHEMA,
        DEST_TABLE
    )

    resource.execute_postgres_sql(
        SQL_DIR / "load_final_order_ecom.sql"
    )

    print("Sync completed.")

finally:
    resource.close()