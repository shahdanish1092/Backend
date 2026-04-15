#!/usr/bin/env python3
import os
import sys
import asyncio
from pathlib import Path

# Ensure workspace root is on sys.path so package imports work when run as a script
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from routers import admin as admin_router

async def main():
    key = os.environ.get("ADMIN_KEY")
    if not key:
        raise RuntimeError("ADMIN_KEY env must be set for sync")
    print("Starting admin sync_workflows...")
    res = await admin_router.sync_workflows(x_admin_key=key)
    print("Sync result:", res)

if __name__ == '__main__':
    asyncio.run(main())
