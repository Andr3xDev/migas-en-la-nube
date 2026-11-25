from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_settings
from app.api.schemas import HealthResponse
from app.core.settings import Settings

router = APIRouter(prefix="/api")


@router.get("/health")
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(status="ok", version=settings.version, environment=settings.environment)
