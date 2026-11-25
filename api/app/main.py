from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import health, products
from app.domain.errors import ConflictError, NotFoundError, RuleViolationError

app = FastAPI()
app.include_router(health.router)
app.include_router(products.router)


def register_error_handler(error: type[Exception], status_code: int) -> None:
    @app.exception_handler(error)
    def handle(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})


register_error_handler(NotFoundError, 404)
register_error_handler(ConflictError, 409)
register_error_handler(RuleViolationError, 422)
