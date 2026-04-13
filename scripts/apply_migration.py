#!/usr/bin/env python3
"""
Apply SQL migration(s) to the target Postgres database.

Usage:
  - Ensure `DATABASE_URL` is set to your Supabase Postgres connection string.
  - Install deps: `pip install -r requirements.txt`
  - Run: `python scripts/apply_migration.py`

This script reads every SQL file in `db/migrations` and executes them in lexicographic order.
"""
import os
import sys
from pathlib import Path

def load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        # dotenv is optional; environment variables may already be present
        pass
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL is not set. Set it to your Supabase Postgres connection string.")
        sys.exit(1)
    return db_url

def run_sql(db_url, sql_text):
    try:
        import psycopg2
    except Exception as e:
        print("ERROR: psycopg2 is not installed. Run: pip install psycopg2-binary")
        raise

    conn = None
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(sql_text)
        conn.commit()
        print("Migration applied successfully.")
    except Exception as e:
        if conn:
            conn.rollback()
        print("Migration failed:", e)
        raise
    finally:
        if conn:
            conn.close()

def main():
    db_url = load_env()
    base = Path(__file__).resolve().parent.parent
    migrations_dir = base / "db" / "migrations"
    sql_files = sorted([path for path in migrations_dir.iterdir() if path.suffix == ".sql"])
    if not sql_files:
        print(f"No migration files found in: {migrations_dir}")
        sys.exit(1)
    for sql_file in sql_files:
        print(f"Applying {sql_file.name}")
        sql_text = sql_file.read_text(encoding="utf-8")
        run_sql(db_url, sql_text)

if __name__ == "__main__":
    main()
