import json
import logging
import re

import pytest
from fastapi.testclient import TestClient

from app.main import app

HEALTH_PATH = "/api/health"
REQUEST_LOGGER = "pdc.request"
CORRELATION_HEADER = "x-correlation-id"


def _access_log(caplog) -> dict:
    lines = [r.getMessage() for r in caplog.records if r.name == REQUEST_LOGGER]
    assert len(lines) == 1
    return json.loads(lines[0])


def test_request_with_correlation_header_logs_json_line_with_that_id(client, caplog):
    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER)

    response = client.get(HEALTH_PATH, headers={CORRELATION_HEADER: "abc-123"})

    entry = _access_log(caplog)
    assert entry["correlation_id"] == "abc-123"
    assert entry["method"] == "GET"
    assert entry["path"] == HEALTH_PATH
    assert entry["status"] == response.status_code
    assert entry["duration_ms"] >= 0
    assert CORRELATION_HEADER not in response.headers


def test_request_without_correlation_header_logs_generated_uuid_hex(client, caplog):
    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER)

    client.get(HEALTH_PATH)

    assert re.fullmatch(r"[0-9a-f]{32}", _access_log(caplog)["correlation_id"])


@pytest.mark.parametrize("bad_id", ["x" * 65, "bad id!<>"])
def test_invalid_correlation_header_is_replaced_by_generated_id(client, caplog, bad_id):
    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER)

    client.get(HEALTH_PATH, headers={CORRELATION_HEADER: bad_id})

    assert re.fullmatch(r"[0-9a-f]{32}", _access_log(caplog)["correlation_id"])


@pytest.fixture
def failing_route():
    # The logging middleware lives on the global app, so the probe route is added and removed there.
    routes_before = list(app.router.routes)

    @app.get("/probe-unhandled-error")
    def probe_unhandled_error():
        raise RuntimeError("boom")

    yield
    app.router.routes[:] = routes_before


def test_unhandled_error_logs_status_500(failing_route, caplog):
    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER)

    TestClient(app, raise_server_exceptions=False).get("/probe-unhandled-error")

    assert _access_log(caplog)["status"] == 500
