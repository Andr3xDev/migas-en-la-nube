import importlib
import sys

import pytest
from fastapi.testclient import TestClient

HEALTH_PATH = "/api/health"


@pytest.fixture
def make_client(monkeypatch):
    """Build a client from a fresh import so settings are read from the current env."""

    def _make(**env: str) -> TestClient:
        for name in ("PDC_VERSION", "PDC_ENVIRONMENT"):
            monkeypatch.delenv(name, raising=False)
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        for module in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
            del sys.modules[module]
        return TestClient(importlib.import_module("app.main").app)

    return _make


def test_get_health_returns_ok_body_with_version_and_environment(make_client):
    response = make_client().get(HEALTH_PATH)

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert isinstance(body["version"], str) and body["version"]
    assert isinstance(body["environment"], str) and body["environment"]


def test_get_health_without_credentials_is_not_rejected(make_client):
    response = make_client().get(HEALTH_PATH)

    assert response.status_code not in (401, 403)


def test_get_health_with_environment_override_returns_it(make_client):
    response = make_client(PDC_ENVIRONMENT="dev").get(HEALTH_PATH)

    assert response.json()["environment"] == "dev"


def test_get_health_with_version_override_returns_it(make_client):
    response = make_client(PDC_VERSION="abc1234").get(HEALTH_PATH)

    assert response.json()["version"] == "abc1234"


def test_get_health_without_env_vars_uses_defaults(make_client):
    response = make_client().get(HEALTH_PATH)

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0", "environment": "local"}
