from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Simple liveness probe for container healthchecks.
    ``GET /health`` returns 200 with a minimal JSON payload.
    """
    return {"status": "ok"}
