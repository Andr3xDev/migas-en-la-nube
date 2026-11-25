from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import admin, auth, health, me, orders, products
from app.domain.errors import (
    INVALID_CREDENTIALS,
    AuthenticationError,
    ConcurrencyConflictError,
    ConflictError,
    NotFoundError,
    RuleViolationError,
)

app = FastAPI()
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(admin.router)
app.include_router(me.router)


def register_error_handler(error: type[Exception], status_code: int) -> None:
    @app.exception_handler(error)
    def handle(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})


@app.exception_handler(AuthenticationError)
def handle_authentication_error(request: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": INVALID_CREDENTIALS})


register_error_handler(NotFoundError, 404)
register_error_handler(ConflictError, 409)
register_error_handler(ConcurrencyConflictError, 409)
register_error_handler(RuleViolationError, 422)
