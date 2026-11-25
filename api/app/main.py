from fastapi import APIRouter, FastAPI

from app.settings import Settings

settings = Settings()
router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": settings.version, "environment": settings.environment}


app = FastAPI()
app.include_router(router)
