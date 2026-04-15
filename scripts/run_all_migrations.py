#!/usr/bin/env python3
"""Run all SQL migrations in db/migrations against a Postgres database.

Usage:
  - Set the `DATABASE_URL` environment variable, or pass the DB URL as first arg.
    $env:DATABASE_URL = 'postgresql://...'; python scripts/run_all_migrations.py
  - The script applies SQL files in lexical order.
"""
import os
import sys
from pathlib import Path

def main():
    db_url = os.environ.get("DATABASE_URL") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not db_url:
        print("ERROR: DATABASE_URL not set. Provide via env or as first arg.", file=sys.stderr)
        sys.exit(1)

    migrations_dir = Path(__file__).resolve().parent.parent / "db" / "migrations"
    if not migrations_dir.exists():
        print(f"ERROR: migrations dir not found: {migrations_dir}", file=sys.stderr)
        sys.exit(1)

    sql_files = sorted([p for p in migrations_dir.iterdir() if p.suffix == ".sql"])
    if not sql_files:
        print("No .sql migration files found in db/migrations", file=sys.stderr)
        sys.exit(1)

    try:
        import psycopg2
    except Exception as exc:
        print("ERROR: psycopg2 is required to run migrations:", exc, file=sys.stderr)
        sys.exit(1)

    print("Connecting to database...")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    conn.autocommit = False
    try:
        for sql_file in sql_files:
            print(f"Applying {sql_file.name}...")
            sql = sql_file.read_text(encoding="utf-8")
            cur.execute(sql)
        conn.commit()
    except Exception as exc:
        conn.rollback()
        print("Migration failed:", exc, file=sys.stderr)
        sys.exit(2)
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    print("Migrations applied successfully")


if __name__ == "__main__":
    main()
"""
Run all SQL files in db/migrations in lexicographic order.

This script is intentionally simple and defers importing psycopg2 until runtime.
"""
import os
from pathlib import Path


def run_all():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL not set")

    migrations_dir = Path(__file__).resolve().parent.parent / "db" / "migrations"
    files = sorted([p for p in migrations_dir.iterdir() if p.suffix == ".sql"])

    import psycopg2

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    for f in files:
        sql = f.read_text(encoding="utf-8")
        cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    run_all()
