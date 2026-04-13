from fastapi import APIRouter

router = APIRouter()


@router.get("/vendors/ping")
async def vendors_ping():
    return {"ok": True, "module": "admin.vendors"}
