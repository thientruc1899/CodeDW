import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pymysql
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

# ---------------- CONFIG ----------------
# Credentials live in .env next to this file (see .env.example). Never commit .env.
load_dotenv()

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

SOURCE_TABLE = "ecom_order"

RAW_SCHEMA = "staging"
DEST_SCHEMA = "staging"
DEST_TABLE = "stg_inform_ecom_order"
DATE_EXPR = "COALESCE(updated_at, created_at)"


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

