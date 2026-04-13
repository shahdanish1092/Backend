from fastapi import APIRouter

router = APIRouter()


@router.get("/approvals/ping")
async def approvals_ping():
    return {"ok": True, "module": "approvals"}
