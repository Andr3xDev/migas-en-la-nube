from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import admin, auth, health, me, orders, products
from app.core.logging import is_valid_correlation_id, log_request
from app.domain.errors import (
    INVALID_CREDENTIALS,
    AuthenticationError,
    ConcurrencyConflictError,
    ConflictError,
    NotFoundError,
    RuleViolationError,
)

CORRELATION_HEADER = "x-correlation-id"

app = FastAPI()
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(admin.router)
app.include_router(me.router)


@app.middleware("http")
async def correlation_logging(request: Request, call_next):
    supplied_id = request.headers.get(CORRELATION_HEADER)
    correlation_id = supplied_id if is_valid_correlation_id(supplied_id) else uuid4().hex
    started = perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        log_request(
            request.method,
            request.url.path,
            status,
            (perf_counter() - started) * 1000,
            correlation_id,
        )


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
