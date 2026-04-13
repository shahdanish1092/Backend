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
