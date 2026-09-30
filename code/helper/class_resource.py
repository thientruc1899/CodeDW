import os
import sys

import pymysql
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values
from pathlib import Path


load_dotenv()


class Resource:

    def __init__(self):

        self.MARIADB = dict(
            host=self.env("INFORM_HOST"),
            port=int(self.env("INFORM_PORT", "3306")),
            user=self.env("INFORM_USER"),
            password=self.env("INFORM_PASSWORD"),
            database=self.env("INFORM_DB"),
        )

        self.POSTGRES = dict(
            host=self.env("DW_HOST"),
            port=int(self.env("DW_PORT", "5432")),
            user=self.env("DW_USER"),
            password=self.env("DW_PASSWORD"),
            dbname=self.env("DW_DB"),
        )

        self.mysql_conn = None
        self.pg_conn = None


    @staticmethod
    def env(key, default=None):

        value = os.getenv(key, default)

        if value is None or value == "":
            sys.exit(f"Missing {key} — set it in .env")

        return value


    # ==================================================
    # CONNECT DATABASE
    # ==================================================

    def connect(self):

        self.mysql_conn = pymysql.connect(
            **self.MARIADB,
            cursorclass=pymysql.cursors.DictCursor
        )

        self.pg_conn = psycopg2.connect(
            **self.POSTGRES
        )

        print("Database connected")


    # ==================================================
    # PULL DATA FROM MARIADB
    # ==================================================

    def pull_by_date(self, query, target_date):

        with self.mysql_conn.cursor() as cur:

            cur.execute(
                query,
                (target_date,)
            )

            rows = cur.fetchall()

        print(f"Rows pulled: {len(rows)}")

        return rows


    # ==================================================
    # INSERT INTO POSTGRES RAW
    # ==================================================

    def insert_postgres(
        self,
        rows,
        dest_schema,
        dest_table
    ):

        if not rows:
            print("No rows to insert")
            return 0

        columns = list(rows[0].keys())

        values = [
            [row[c] for c in columns]
            for row in rows
        ]

        column_sql = ", ".join(
            f'"{c}"' for c in columns
        )

        query = f"""
            INSERT INTO {dest_schema}.{dest_table}
            ({column_sql})
            VALUES %s
        """

        try:

            with self.pg_conn.cursor() as cur:

                execute_values(
                    cur,
                    query,
                    values
                )

            self.pg_conn.commit()

            print(
                f"Inserted {len(rows)} rows into: "
                f"{dest_schema}.{dest_table}"
            )

            return len(rows)

        except Exception:

            self.pg_conn.rollback()
            raise


    # ==================================================
    # EXECUTE POSTGRES SQL FILE
    # ==================================================

    def execute_postgres_sql(self, sql_file):

        sql_file = Path(sql_file)

        if not sql_file.exists():
            raise FileNotFoundError(
                f"SQL file not found: {sql_file}"
            )

        sql = sql_file.read_text(
            encoding="utf-8"
        )

        try:

            with self.pg_conn.cursor() as cur:
                cur.execute(sql)

            self.pg_conn.commit()

            print(
                f"Executed SQL: {sql_file.name}"
            )

        except Exception:

            self.pg_conn.rollback()

            print(
                f"Failed SQL: {sql_file.name}"
            )

            raise


    # ==================================================
    # CLOSE DATABASE
    # ==================================================

    def close(self):

        if self.mysql_conn:
            self.mysql_conn.close()

        if self.pg_conn:
            self.pg_conn.close()

        print("Database connections closed")