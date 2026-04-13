from fastapi import FastAPI, Header, HTTPException
import os
from pathlib import Path

app = FastAPI()


@app.post("/internal/run_migrations")
async def run_migrations(x_automation_secret: str | None = Header(None)):
    web_secret = os.getenv("WEBHOOK_SECRET")
    if not web_secret:
        raise HTTPException(status_code=500, detail="Server misconfigured: WEBHOOK_SECRET not set")
    if x_automation_secret != web_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(status_code=500, detail="Server misconfigured: DATABASE_URL not set")

    migrations_dir = Path(__file__).resolve().parent.parent / "db" / "migrations"
    sql_files = sorted([path for path in migrations_dir.iterdir() if path.suffix == ".sql"])
    if not sql_files:
        raise HTTPException(status_code=500, detail="Migration files not found")

    try:
        import psycopg2
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
        cur = conn.cursor()
        for sql_file in sql_files:
            cur.execute(sql_file.read_text(encoding="utf-8"))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {e}")

    return {"status": "ok", "detail": "Migrations applied"}
