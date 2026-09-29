#!/usr/bin/env python3
"""
Daily sync: MariaDB -> PostgreSQL
ibasicco_aftm2.ecom_order -> staging.stg_inform_ecom_order

Pulls all rows from the previous calendar day, based on
COALESCE(updated_at, created_at) (falls back to created_at when
updated_at is null). Inserts them into Postgres. No dedup — if a row
was already synced on an earlier date and gets updated, it will be
inserted again alongside the old copy. Duplicates are OK for now.

------------------------------------------------------------------------
Destination table reference
------------------------------------------------------------------------

Query used against MariaDB to inspect the source table's schema:

    SELECT column_name, data_type, column_type, numeric_precision,
           numeric_scale, ordinal_position
    FROM information_schema.columns
    WHERE table_schema = 'ibasicco_aftm2'
      AND table_name = 'ecom_order'
    ORDER BY ordinal_position;

CREATE TABLE statement used to create the Postgres destination table
(no primary key — staging table, duplicates OK):

    CREATE SCHEMA IF NOT EXISTS staging;

    CREATE TABLE staging.stg_inform_ecom_order (
        "id" integer,
        "order_id" text,
        "rso_name" text,
        "channel" text,
        "customer_id" text,
        "customer_name" text,
        "order_flag" text,
        "deadline" timestamp,
        "delivery_at" timestamp,
        "fulfillment_at" timestamp,
        "complete_at" timestamp,
        "cancel_at" timestamp,
        "status" smallint,
        "ps_status" text,
        "picking_status" smallint,
        "picking_name" text,
        "total_items" smallint,
        "total_amount" real,
        "net_price" real,
        "address_shipping" text,
        "phone_shipping" text,
        "customer_note" text,
        "packing_note" text,
        "repick_stt" smallint,
        "repick_note" text,
        "shipping_carrier" text,
        "cron_handle_detail" text,
        "uic_id" integer,
        "uic_name" text,
        "get_by" text,
        "warehouse" text,
        "location_id" integer,
        "created_at" timestamp,
        "updated_at" timestamp,
        "updated_id" integer,
        "package_code" text
    );
------------------------------------------------------------------------

------------------------------------------------------------------------
Deduped "final" table: staging.stg_ecom_order_final
------------------------------------------------------------------------

stg_inform_ecom_order can contain multiple rows per id (each sync run
inserts fresh rows with no dedup). stg_ecom_order_final holds only the
single most-recent row per id, based on updated_at.

1. One-time creation, deduping the entire staging table using
   ROW_NUMBER() partitioned by id, keeping the most recently updated row:

    CREATE TABLE staging.stg_ecom_order_final AS
    SELECT
        "id", "order_id", "rso_name", "channel", "customer_id", "customer_name",
        "order_flag", "deadline", "delivery_at", "fulfillment_at", "complete_at",
        "cancel_at", "status", "ps_status", "picking_status", "picking_name",
        "total_items", "total_amount", "net_price", "address_shipping",
        "phone_shipping", "customer_note", "packing_note", "repick_stt",
        "repick_note", "shipping_carrier", "cron_handle_detail", "uic_id",
        "uic_name", "get_by", "warehouse", "location_id", "created_at",
        "updated_at", "updated_id", "package_code"
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC) AS rn
        FROM staging.stg_inform_ecom_order
    ) ranked
    WHERE rn = 1;

2. (Considered but not used) Adding a unique constraint on id, which
   would allow a true ON CONFLICT upsert instead of delete+insert:

    ALTER TABLE staging.stg_ecom_order_final
    ADD CONSTRAINT stg_ecom_order_final_id_unique UNIQUE ("id");

   Went with delete+insert instead (below), so this constraint was not
   actually applied.

3. Daily incremental update: pull yesterday's ids from
   stg_inform_ecom_order, delete any matching ids from the final table,
   then insert the deduped fresh rows for those ids. Wrapped in a
   transaction so a failure can't leave the delete applied without the
   matching insert.

    BEGIN;

    DELETE FROM staging.stg_ecom_order_final
    WHERE "id" IN (
        SELECT DISTINCT "id"
        FROM staging.stg_inform_ecom_order
        WHERE DATE(COALESCE(updated_at, created_at)) = CURRENT_DATE - INTERVAL '1 day'
    );

    INSERT INTO staging.stg_ecom_order_final
    SELECT
        "id", "order_id", "rso_name", "channel", "customer_id", "customer_name",
        "order_flag", "deadline", "delivery_at", "fulfillment_at", "complete_at",
        "cancel_at", "status", "ps_status", "picking_status", "picking_name",
        "total_items", "total_amount", "net_price", "address_shipping",
        "phone_shipping", "customer_note", "packing_note", "repick_stt",
        "repick_note", "shipping_carrier", "cron_handle_detail", "uic_id",
        "uic_name", "get_by", "warehouse", "location_id", "created_at",
        "updated_at", "updated_id", "package_code"
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (PARTITION BY "id" ORDER BY updated_at DESC) AS rn
        FROM staging.stg_inform_ecom_order
        WHERE DATE(COALESCE(updated_at, created_at)) = CURRENT_DATE - INTERVAL '1 day'
    ) ranked
    WHERE rn = 1;

    COMMIT;

Note: this final-table maintenance (steps 1-3 above) is not yet wired
into this Python script — it currently only handles the raw insert into
stg_inform_ecom_order. The final-table update is still run manually in
Postgres.
------------------------------------------------------------------------

Setup:
    pip install pymysql psycopg2-binary
    python3 sync_ecom_order.py
"""

from datetime import date, timedelta

import pymysql
import psycopg2
from psycopg2.extras import execute_values

# ---------------- CONFIG ----------------
SOURCE_TABLE = "ecom_order"
DEST_SCHEMA = "staging"
DEST_TABLE = "stg_inform_ecom_order"
DATE_EXPR = "COALESCE(updated_at, created_at)"

MARIADB = dict(
    host="103.221.223.22",
    user="ibasicco_ba",
    password="1p[$PH,g{er}O3C6",
    database="ibasicco_aftm2",
)

POSTGRES = dict(
    host="103.57.210.57",
    user="postgres",
    password="Aa@123456!",
    dbname="db_bi",
)
# -----------------------------------------

target_date = date.today() - timedelta(days=1)
print(f"Pulling data for date: {target_date}")

mysql_conn = pymysql.connect(**MARIADB, cursorclass=pymysql.cursors.DictCursor)
pg_conn = psycopg2.connect(**POSTGRES)

# 1. Pull yesterday's rows from MariaDB (by updated_at, falling back to created_at)
with mysql_conn.cursor() as cur:
    cur.execute(
        f"SELECT * FROM {SOURCE_TABLE} WHERE DATE({DATE_EXPR}) = %s",
        (target_date,),
    )
    rows = cur.fetchall()

print(f"Rows pulled: {len(rows)}")

# 2. Insert into Postgres (no dedup — duplicates OK for now)
if rows:
    columns = list(rows[0].keys())
    values = [[row[c] for c in columns] for row in rows]

    query = f"""
        INSERT INTO {DEST_SCHEMA}.{DEST_TABLE} ({", ".join(f'"{c}"' for c in columns)})
        VALUES %s
    """
    with pg_conn.cursor() as cur:
        execute_values(cur, query, values)
    pg_conn.commit()
    print(f"Inserted {len(rows)} rows into {DEST_SCHEMA}.{DEST_TABLE}")

mysql_conn.close()
pg_conn.close()
