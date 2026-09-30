import sys
from pathlib import Path
from datetime import date, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


SQL_DIR = PROJECT_ROOT / "sql"

from helper.class_resource import Resource

DEST_SCHEMA = "staging"

target_date = date.today() - timedelta(days=1)

print(f"Pulling data for date: {target_date}")


# ==============================
# SQL ECOM ORDER
# ==============================

sql_order = """
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
    # ==========================================
    # 1. Connect DB
    # ==========================================
    resource.connect()

    # ==========================
    # 2. MariaDB -> RAW
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


    # ==========================================
    # 3. RAW -> FINAL
    # ==========================================

    resource.execute_postgres_sql(
        SQL_DIR / "load_final_table.sql"
    )


finally:
    resource.close()
