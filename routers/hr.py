from fastapi import APIRouter

router = APIRouter()


@router.get("/hr/ping")
async def hr_ping():
    return {"ok": True, "module": "hr"}
