import sys
from pathlib import Path
from datetime import date, datetime, timedelta, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SQL_DIR = PROJECT_ROOT / "sql"

from helper.class_resource import Resource


DEST_SCHEMA = "staging"
DEST_TABLE = "stg_inform_customer"

VN_TZ = timezone(timedelta(hours=7))


# ==============================
# SQL
# ==============================

# Đổi "customers" nếu bảng khách trên Inform tên khác
SOURCE_TABLE = "customers"

COLUMNS = """
    c.id,
    c.hrv_id,
    c.phone,
    c.full_name,
    c.email,
    c.birthday,
    c.gender,
    c.level,
    c.total_point,
    c.total_purchase,
    c.street,
    c.ward,
    c.district,
    c.province,
    c.last_online_order,
    c.last_offline_order,
    c.last_date_order,
    c.last_online_date,
    c.last_offline_date,
    c.created_at,
    c.updated_at
"""

# Khách có thay đổi trong ngày (điểm, hạng, đơn cuối... đều làm updated_at đổi)
SQL_BY_DATE = f"""
    SELECT {COLUMNS}
    FROM {SOURCE_TABLE} c
    WHERE (c.updated_at >= %(start)s AND c.updated_at < %(end)s)
       OR (c.updated_at IS NULL AND c.created_at >= %(start)s AND c.created_at < %(end)s)
"""

# Nạp lần đầu: kéo toàn bộ
SQL_FULL = f"SELECT {COLUMNS} FROM {SOURCE_TABLE} c"


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
    full_mode = len(sys.argv) > 1 and sys.argv[1].lower() == "full"

    resource = Resource()

    try:
        resource.connect()

        # 1. MariaDB -> STAGING
        if full_mode:
            print("FULL load customers...")
            rows = resource.pull(SQL_FULL)
            resource.insert_postgres(rows, DEST_SCHEMA, DEST_TABLE)
        else:
            target_dates = get_target_dates(sys.argv)
            print(f"Dates to pull: {target_dates[0]} -> {target_dates[-1]} ({len(target_dates)} day)")

            for d in target_dates:
                print(f"Syncing CUSTOMER for {d}...")
                rows = resource.pull(
                    SQL_BY_DATE,
                    {"start": d, "end": d + timedelta(days=1)},
                )
                resource.insert_postgres(rows, DEST_SCHEMA, DEST_TABLE)

        # 2. STAGING -> DIM
        print("Loading dim_customer...")
        resource.execute_postgres_sql(SQL_DIR / "load_dim_customer.sql")

    finally:
        resource.close()


if __name__ == "__main__":
    main()
