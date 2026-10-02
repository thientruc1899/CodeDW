import os
from pathlib import Path

import pymysql
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

load_dotenv()


class Resource:

    def __init__(self):
        self.mysql_conn = None
        self.pg_conn = None

    # ==================================================
    # CONNECT
    # ==================================================

    def connect(self):

        self.mysql_conn = pymysql.connect(
            host=os.getenv("INFORM_HOST"),
            port=int(os.getenv("INFORM_PORT", "3306")),
            user=os.getenv("INFORM_USER"),
            password=os.getenv("INFORM_PASSWORD"),
            database=os.getenv("INFORM_DB"),
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )

        self.pg_conn = psycopg2.connect(
            host=os.getenv("DW_HOST"),
            port=int(os.getenv("DW_PORT", "5432")),
            user=os.getenv("DW_USER"),
            password=os.getenv("DW_PASSWORD"),
            dbname=os.getenv("DW_DB"),
            options="-c timezone=Asia/Ho_Chi_Minh",   # để CURRENT_DATE đúng giờ VN
        )

        print("Database connected")

    # ==================================================
    # MARIADB -> RAM
    # ==================================================

    def pull_by_params(self, query, params):

        with self.mysql_conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

        print(f"Rows pulled: {len(rows)}")

        return rows

    # ==================================================
    # RAM -> POSTGRES
    # ==================================================

    def insert_postgres(self, rows, dest_schema, dest_table):

        if not rows:
            print("No rows to insert")
            return 0

        columns = list(rows[0].keys())

        values = [
            [row[c] for c in columns]
            for row in rows
        ]

        column_sql = ", ".join(f'"{c}"' for c in columns)

        query = f"""
            INSERT INTO {dest_schema}.{dest_table}
            ({column_sql})
            VALUES %s
        """

        with self.pg_conn.cursor() as cur:
            execute_values(cur, query, values, page_size=1000)

        self.pg_conn.commit()

        print(f"Inserted {len(rows)} rows into {dest_schema}.{dest_table}")

        return len(rows)

    # ==================================================
    # RUN SQL LOAD TO FINAL TABLE
    # ==================================================

    def execute_postgres_sql(self, sql_file):

        sql_file = Path(sql_file)
        sql = sql_file.read_text(encoding="utf-8")

        with self.pg_conn.cursor() as cur:
            cur.execute(sql)

        self.pg_conn.commit()

        print(f"Executed SQL: {sql_file.name}")

    # ==================================================
    # CLOSE
    # ==================================================

    def close(self):
        try:
            if self.mysql_conn:
                self.mysql_conn.close()
        except Exception as e:
            print(f"Error closing mysql: {e}")

        try:
            if self.pg_conn:
                self.pg_conn.close()
        except Exception as e:
            print(f"Error closing postgres: {e}")

        print("Database connections closed")