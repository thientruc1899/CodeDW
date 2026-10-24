import sys
from pathlib import Path
from datetime import date, datetime, timedelta, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SQL_DIR = PROJECT_ROOT / "sql"

from helper.class_resource import Resource


DEST_SCHEMA = "staging"
DEST_TABLE = "stg_inform_retail_order_detail"

VN_TZ = timezone(timedelta(hours=7))


# ==============================
# SQL
# ==============================
SQL_DETAIL = """
    SELECT d.*
    FROM hrv_retail_orders o
    INNER JOIN hrv_retail_order_details d
        ON o.order_id = d.order_id
    WHERE (o.updated_at >= %(start)s AND o.updated_at < %(end)s)
       OR (o.updated_at IS NULL AND o.created_at >= %(start)s AND o.created_at < %(end)s)
"""

# ==============================
# HELPERS
# ==============================

def get_target_dates(argv):
    """Không truyền gì -> hôm qua. 1 ngày -> ngày đó. 2 ngày -> cả khoảng."""
    if len(argv) < 2:
        return [datetime.now(VN_TZ).date() - timedelta(days=1)]

    start = date.fromisoformat(argv[1])
    end = date.fromisoformat(argv[2]) if len(argv) > 2 else start

    if end < start:
        raise ValueError(f"end_date ({end}) phải >= start_date ({start})")

    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


# ==============================
# RUN
# ==============================

def main():
    target_dates = get_target_dates(sys.argv)
    print(f"Dates to pull: {target_dates[0]} -> {target_dates[-1]} ({len(target_dates)} day)")

    resource = Resource()

    try:
        # 1. Connect DB
        resource.connect()

        # 2. MariaDB -> STAGING (từng ngày)
        for d in target_dates:
            print(f"Syncing RETAIL DETAIL for {d}...")
            rows_detail = resource.pull(
                SQL_DETAIL,
                {"start": d, "end": d + timedelta(days=1)},
            )
            resource.insert_postgres(rows_detail, DEST_SCHEMA, DEST_TABLE)

        # 3. STAGING -> FINAL (1 lần, dùng watermark nên nạp bù được batch bị lỡ)
        print("Loading final...")
        resource.execute_postgres_sql(SQL_DIR / "load_final_retail_detail.sql")

    finally:
        resource.close()


if __name__ == "__main__":
    main()