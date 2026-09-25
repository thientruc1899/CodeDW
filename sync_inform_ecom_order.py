#!/usr/bin/env python3
"""
Daily sync: MariaDB -> PostgreSQL (order-line grain)

    ibasicco_aftm2.ecom_order + ecom_order_detail
        -> staging.stg_inform_ecom_order_line   (raw, append-only, duplicates OK)
        -> public.ecom_order_final              (1 row per line id, kept current)

Grain: 1 row = 1 order line (id = ecom_order_detail b.id).

Daily filter: DATE(COALESCE(a.updated_at, a.created_at)) = target date
(orders created OR updated that day). Fixed filters from the source
query are kept: c.id IS NOT NULL, c.canceled = 0, a.status <> -1.

Final table update, inside the same transaction as the raw insert:
    1. DELETE every line whose order was touched that day (by order_id,
       taken from ecom_order directly — NOT from the filtered result).
       This also drops lines that got canceled / orders that went to
       status -1 since last sync, which the filtered query no longer
       returns and would otherwise linger in the final table forever.
    2. INSERT the fresh snapshot. One pull = one snapshot, so each line
       id appears once -> no ROW_NUMBER dedup needed.
Re-running for the same date is safe (raw table gets duplicates, final
table ends up identical).

Both tables are created automatically if missing (DDL generated from
COLUMNS below). Source schema check, if needed:

    SELECT column_name, data_type, column_type
    FROM information_schema.columns
    WHERE table_schema = 'ibasicco_aftm2'
      AND table_name IN ('ecom_order', 'ecom_order_detail')
    ORDER BY table_name, ordinal_position;

Setup:
    pip install pymysql psycopg2-binary python-dotenv
    cp .env.example .env    # then fill in credentials
    python3 sync_ecom_order_line.py               # yesterday
    python3 sync_ecom_order_line.py 2026-09-20    # specific date (backfill)
"""

import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pymysql
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

# ---------------- CONFIG ----------------
RAW_SCHEMA = "staging"
RAW_TABLE = "stg_inform_ecom_order_line"
FINAL_SCHEMA = "public"
FINAL_TABLE = "ecom_order_final"
SYNC_FINAL = True  # set False to only append to the raw table

RAW = f"{RAW_SCHEMA}.{RAW_TABLE}"
FINAL = f"{FINAL_SCHEMA}.{FINAL_TABLE}"

# Credentials live in .env next to this file (see .env.example). Never commit .env.
load_dotenv(Path(__file__).resolve().parent / ".env")


def env(key: str, default: str | None = None) -> str:
    value = os.getenv(key, default)
    if value is None or value == "":
        sys.exit(f"Missing {key} — set it in .env")
    return value


MARIADB = dict(
    host=env("INFORM_HOST"),
    port=int(env("INFORM_PORT", "3306")),
    user=env("INFORM_USER"),
    password=env("INFORM_PASSWORD"),
    database=env("INFORM_DB"),
)

POSTGRES = dict(
    host=env("DW_HOST"),
    port=int(env("DW_PORT", "5432")),
    user=env("DW_USER"),
    password=env("DW_PASSWORD"),
    dbname=env("DW_DB"),
)
# -----------------------------------------

# Output columns of SOURCE_SQL, in order, with the Postgres type used
# for both destination tables.
COLUMNS = [
    ("id", "integer"),
    ("order_id", "integer"),
    ("order_name", "text"),
    ("order_date", "timestamp"),
    ("completed_date", "timestamp"),
    ("order_status", "smallint"),
    ("type_lv2", "text"),
    ("type_lv1", "text"),
    ("origin_customer_id", "text"),
    ("customer_id", "text"),
    ("customer_info", "text"),
    ("sale_man", "text"),
    ("location_hrv_id", "text"),
    ("location_name", "text"),
    ("channel_id", "integer"),
    ("model_sku", "text"),
    ("variant_id", "text"),  # switch to bigint if product_variant_id is numeric in source
    ("barcode", "text"),
    ("promotion_name", "text"),
    ("partner_discount", "numeric"),
    ("vat_contract", "numeric"),
    ("vat_current", "numeric"),
    ("qty_ordered", "integer"),
    ("qty_delivered", "integer"),
    ("gross_revenue", "numeric"),
    ("net_revenue_bf_coupon", "numeric"),
    ("net_revenue", "numeric"),
    ("net_revenue_actual", "numeric"),
    ("coupon_amount", "numeric"),
    ("note", "text"),
    ("warehouse_id", "integer"),
    ("warehouse_name", "text"),
    ("warehouse_status", "smallint"),
    ("warehouse_date", "timestamp"),
    ("return_name", "text"),
    ("data_source", "text"),
    ("updated_at", "timestamp"),
]
COL_NAMES = [c for c, _ in COLUMNS]
COL_LIST = ", ".join(f'"{c}"' for c in COL_NAMES)

# NOTE: pymysql formats the query with %-style params, so every literal
# '%' in LIKE patterns must be written as '%%'.
SOURCE_SQL = """
SELECT
    b.id,
    a.id                    AS order_id,
    a.order_id              AS order_name,
    a.created_at            AS order_date,
    a.delivery_at           AS completed_date,
    a.`status`              AS order_status,
    CASE
        WHEN UPPER(a.customer_note) LIKE '%%THU COD%%' THEN 'Sale - Exchange'
        ELSE 'Sale - Sale'
    END                     AS type_lv2,
    'Sale'                  AS type_lv1,
    a.customer_id           AS origin_customer_id,
    a.customer_name         AS customer_id,
    'No'                    AS customer_info,
    a.uic_name              AS sale_man,
    ''                      AS location_hrv_id,
    a.channel               AS location_name,
    CASE
        WHEN a.channel = 'Shopee2'                THEN 50004  -- must come before 'Shopee%%'
        WHEN a.channel LIKE 'Shopee%%'            THEN 50001
        WHEN a.channel = 'Lazada'                 THEN 50002
        WHEN a.channel = 'Lazada2'                THEN 50005
        WHEN a.channel = 'Tiki'                   THEN 50003
        WHEN a.channel IN ('Tiktok', 'Tiktok2')   THEN 60001
        ELSE 0
    END                     AS channel_id,
    b.old_sku               AS model_sku,
    c.product_variant_id    AS variant_id,
    c.barcode,
    ''                      AS promotion_name,
    0                       AS partner_discount,
    0.08                    AS vat_contract,
    0.08                    AS vat_current,
    (c.quan - c.canceled)                   AS qty_ordered,
    (c.quan - c.canceled)                   AS qty_delivered,
    (c.quan - c.canceled) * c.origin_price  AS gross_revenue,
    (c.quan - c.canceled) * c.paid_price    AS net_revenue_bf_coupon,
    (c.quan - c.canceled) * c.paid_price    AS net_revenue,
    (c.quan - c.canceled) * c.net_price     AS net_revenue_actual,
    0                       AS coupon_amount,
    a.customer_note         AS note,
    a.location_id           AS warehouse_id,
    a.picking_name          AS warehouse_name,
    a.picking_status        AS warehouse_status,
    a.delivery_at           AS warehouse_date,
    ''                      AS return_name,
    'ecom_order_inform'     AS data_source,
    a.updated_at
FROM ecom_order a
    INNER JOIN ecom_order_detail b ON a.order_id = b.order_id
    INNER JOIN ecom_order_detail c ON b.id = c.parent_id
WHERE DATE(COALESCE(a.updated_at, a.created_at)) = %s
  AND c.id IS NOT NULL
  AND c.canceled = 0
  AND a.`status` NOT IN (-1)
"""

# All orders touched on the target date, regardless of status/cancel
# filters — used to clear stale lines from the final table.
TOUCHED_ORDERS_SQL = """
SELECT id
FROM ecom_order
WHERE DATE(COALESCE(updated_at, created_at)) = %s
"""


def ddl(qualified_table: str) -> str:
    cols = ",\n".join(f'    "{c}" {t}' for c, t in COLUMNS)
    return f"CREATE TABLE IF NOT EXISTS {qualified_table} (\n{cols}\n)"


def main() -> None:
    if len(sys.argv) > 1:
        target_date = date.fromisoformat(sys.argv[1])
    else:
        target_date = date.today() - timedelta(days=1)
    print(f"Pulling data for date: {target_date}")

    # 1. Pull from MariaDB
    mysql_conn = pymysql.connect(**MARIADB, cursorclass=pymysql.cursors.DictCursor)
    try:
        with mysql_conn.cursor() as cur:
            cur.execute(SOURCE_SQL, (target_date,))
            rows = cur.fetchall()
            cur.execute(TOUCHED_ORDERS_SQL, (target_date,))
            touched_order_ids = [r["id"] for r in cur.fetchall()]
    finally:
        mysql_conn.close()

    print(f"Lines pulled: {len(rows)}  |  orders touched: {len(touched_order_ids)}")

    if rows:
        missing = set(COL_NAMES) - set(rows[0].keys())
        if missing:
            raise RuntimeError(f"Source query is missing columns: {sorted(missing)}")
    values = [tuple(row[c] for c in COL_NAMES) for row in rows]

    # 2. Write to Postgres — one transaction, commit on success / rollback on error
    pg_conn = psycopg2.connect(**POSTGRES)
    try:
        with pg_conn:
            with pg_conn.cursor() as cur:
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {RAW_SCHEMA}")
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {FINAL_SCHEMA}")
                cur.execute(ddl(RAW))
                cur.execute(ddl(FINAL))

                # 2a. Raw table: append only
                if values:
                    execute_values(
                        cur,
                        f"INSERT INTO {RAW} ({COL_LIST}) VALUES %s",
                        values,
                        page_size=1000,
                    )
                    print(f"Inserted {len(values)} rows into {RAW}")

                # 2b. Final table: delete touched orders, insert fresh snapshot
                if SYNC_FINAL:
                    if touched_order_ids:
                        cur.execute(
                            f'DELETE FROM {FINAL} WHERE "order_id" = ANY(%s)',
                            (touched_order_ids,),
                        )
                        print(f"Deleted {cur.rowcount} rows from {FINAL}")
                    if values:
                        execute_values(
                            cur,
                            f"INSERT INTO {FINAL} ({COL_LIST}) VALUES %s",
                            values,
                            page_size=1000,
                        )
                        print(f"Inserted {len(values)} rows into {FINAL}")
    finally:
        pg_conn.close()

    print("Done.")


if __name__ == "__main__":
    main()