#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from datetime import date, timedelta

import pymysql
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values


STAGING_TABLE = "staging.stg_inform_ecom_order_line"
PUBLIC_TABLE = "public.ecom_order_final"

load_dotenv()


MYSQL_CONFIG = {
    "host": os.getenv("INFORM_HOST"),
    "port": int(os.getenv("INFORM_PORT", 3306)),
    "user": os.getenv("INFORM_USER"),
    "password": os.getenv("INFORM_PASSWORD"),
    "database": os.getenv("INFORM_DB"),
    "cursorclass": pymysql.cursors.DictCursor
}

PG_CONFIG = {
    "host": os.getenv("DW_HOST"),
    "port": int(os.getenv("DW_PORT", 5432)),
    "user": os.getenv("DW_USER"),
    "password": os.getenv("DW_PASSWORD"),
    "dbname": os.getenv("DW_DB")
}


COLUMNS = [
    "id","order_id","order_name","order_date","completed_date",
    "order_status","type_lv2","type_lv1","origin_customer_id",
    "customer_id","customer_info","sale_man","location_hrv_id",
    "location_name","channel_id","model_sku","variant_id",
    "barcode","promotion_name","partner_discount","vat_contract",
    "vat_current","qty_ordered","qty_delivered","gross_revenue",
    "net_revenue_bf_coupon","net_revenue","net_revenue_actual",
    "coupon_amount","note","warehouse_id","warehouse_name",
    "warehouse_status","warehouse_date","return_name",
    "data_source","updated_at"
]

COL_LIST = ",".join(f'"{c}"' for c in COLUMNS)



def load_sql():

    base_dir = Path(__file__).resolve().parent

    path = base_dir / "sql" / "order_ecom.sql"

    if not path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy file: {path}"
        )

    sql = path.read_text(
        encoding="utf-8"
    )

    return sql



def main():

    sync_date = (
        sys.argv[1]
        if len(sys.argv) > 1
        else (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    )

    print(f"Sync date: {sync_date}")

    mysql_conn = pymysql.connect(**MYSQL_CONFIG)

    try:
        with mysql_conn.cursor() as cur:
            cur.execute(load_sql(), (
                    sync_date,
                    sync_date
                ))
            rows = cur.fetchall()
    finally:
        mysql_conn.close()

    print(f"Source rows: {len(rows)}")

    if not rows:
        return

    values = [
        tuple(row[c] for c in COLUMNS)
        for row in rows
    ]

    pg_conn = psycopg2.connect(**PG_CONFIG)

    try:
        with pg_conn:
            with pg_conn.cursor() as cur:

                execute_values(
                    cur,
                    f"""
                    INSERT INTO {STAGING_TABLE}
                    ({COL_LIST})
                    VALUES %s
                    """,
                    values,
                    page_size=1000
                )

                print(f"Inserted staging: {len(values)}")


                cur.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM {STAGING_TABLE} s
                    INNER JOIN {PUBLIC_TABLE} p
                    ON s.id = p.id
                    """
                )

                print(
                    f"Duplicate: {cur.fetchone()[0]}"
                )


                cur.execute(
                    f"""
                    DELETE FROM {PUBLIC_TABLE} p
                    USING {STAGING_TABLE} s
                    WHERE p.id = s.id
                    """
                )

                print(
                    f"Deleted public: {cur.rowcount}"
                )


                cur.execute(
                    f"""
                    INSERT INTO {PUBLIC_TABLE}
                    ({COL_LIST})
                    SELECT {COL_LIST}
                    FROM {STAGING_TABLE}
                    """
                )

                print(
                    f"Inserted public: {cur.rowcount}"
                )

        print("SYNC DONE")

    finally:
        pg_conn.close()


if __name__ == "__main__":
    main()
