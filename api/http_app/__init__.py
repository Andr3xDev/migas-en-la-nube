import azure.functions as func

from app.main import app as fastapi_app


# v1 model: SWA managed Functions need function.json; the v2 AsgiFunctionApp failed to deploy.
async def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    return await func.AsgiMiddleware(fastapi_app).handle_async(req, context)
