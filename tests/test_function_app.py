import asyncio
import json
from pathlib import Path

import azure.functions as func

from http_app import main

FUNCTION_JSON = Path(__file__).parent.parent / "api" / "http_app" / "function.json"


def test_function_json_is_anonymous_catch_all():
    config = json.loads(FUNCTION_JSON.read_text())
    trigger = config["bindings"][0]
    assert config["scriptFile"] == "__init__.py"
    assert trigger["authLevel"] == "anonymous"
    assert trigger["route"] == "{*route}"


def test_main_serves_health_through_asgi():
    req = func.HttpRequest("GET", "/api/health", headers={}, body=b"")
    response = asyncio.run(main(req, None))
    assert response.status_code == 200
