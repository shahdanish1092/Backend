from fastapi import APIRouter

router = APIRouter()


@router.get("/meetings/ping")
async def meetings_ping():
    return {"ok": True, "module": "meetings"}
