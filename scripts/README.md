# Scripts

How to run the helper scripts for deployment verification and migrations.

Prerequisites
- Create and activate your virtualenv and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt
```

Verify environment variables
- Run the env var scanner which will print a table of discovered env vars and write `.env.example`:

```bash
python scripts/verify_env_vars.py
```

Run DB migrations
- This repository uses SQL files under `db/migrations`.
- To apply them against the `DATABASE_URL` in your environment:

```bash
export DATABASE_URL="postgresql://..."
python scripts/run_migrations.py
```

E2E test
- To run the E2E test against a deployed backend set either `BACKEND_PUBLIC_URL` or `RUN_E2E=1` and run pytest:

```bash
BACKEND_PUBLIC_URL=https://backend-production.example python -m pytest tests/e2e_workflow_test.py -q -s
```

Notes
- The migration script executes files in lexical order from `db/migrations`.
- The env verifier will exit non-zero when required vars are missing.
