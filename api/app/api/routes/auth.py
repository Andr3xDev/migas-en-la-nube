from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_auth_provider
from app.api.schemas import Credentials, TokenResponse, UserResponse
from app.ports.auth import AuthProvider

router = APIRouter(prefix="/api/auth")


@router.post("/register", status_code=201)
def register(
    credentials: Credentials, auth: Annotated[AuthProvider, Depends(get_auth_provider)]
) -> UserResponse:
    user = auth.register(credentials.email, credentials.password)
    return UserResponse(id=user.id, email=user.email, role=user.role)


@router.post("/login")
def login(
    credentials: Credentials, auth: Annotated[AuthProvider, Depends(get_auth_provider)]
) -> TokenResponse:
    return TokenResponse(access_token=auth.login(credentials.email, credentials.password))
