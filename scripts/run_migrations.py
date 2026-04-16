#!/usr/bin/env python3
"""Run SQL migrations from db/migrations against DATABASE_URL.

Prints tables before/after, runs SQL files in filename order, and prints row counts for key tables.
Exits 0 on success, 1 on failure.
"""
import os
import sys
import glob
import psycopg2
from psycopg2 import sql


def get_tables(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;")
        return [r[0] for r in cur.fetchall()]


def row_count(conn, table):
    with conn.cursor() as cur:
        cur.execute(sql.SQL("SELECT count(*) FROM {};").format(sql.Identifier(table)))
        return cur.fetchone()[0]


def run_migrations(conn, migrations_dir):
    sql_files = sorted(glob.glob(os.path.join(migrations_dir, "*.sql")))
    if not sql_files:
        print("No SQL migration files found in", migrations_dir)
        return

    for f in sql_files:
        print("Applying:", os.path.basename(f))
        with open(f, "r", encoding="utf-8") as fh:
            content = fh.read()
        try:
            with conn.cursor() as cur:
                cur.execute(content)
            conn.commit()
            print("  OK")
        except Exception as e:
            conn.rollback()
            print("  FAILED:", str(e))
            raise


def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL is not set. Set the environment variable and retry.")
        sys.exit(1)

    migrations_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "migrations")
    print("Migrations directory:", migrations_dir)

    try:
        conn = psycopg2.connect(db_url)
    except Exception as e:
        print("Failed to connect to database:", e)
        sys.exit(1)

    try:
        print("Tables before:")
        before = get_tables(conn)
        for t in before:
            print(" -", t)

        # Print row counts for key tables if present
        for key in ("execution_logs", "workflows"):
            if key in before:
                print(f"Rows in {key}: {row_count(conn, key)}")

        run_migrations(conn, migrations_dir)

        print("Tables after:")
        after = get_tables(conn)
        for t in after:
            print(" -", t)

        for key in ("execution_logs", "workflows"):
            if key in after:
                print(f"Rows in {key}: {row_count(conn, key)}")

    except Exception as e:
        print("Migration run failed:", str(e))
        sys.exit(1)
    finally:
        conn.close()

    print("Migrations completed successfully")
    sys.exit(0)


if __name__ == "__main__":
    main()
