import pytest

from app.core.settings import Settings, get_settings

HEALTH_PATH = "/api/health"


@pytest.fixture
def make_client(client, monkeypatch):
    """Serve settings read from the current env instead of the cached ones."""

    def _make(**env: str):
        for name in ("PDC_VERSION", "PDC_ENVIRONMENT"):
            monkeypatch.delenv(name, raising=False)
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        client.app.dependency_overrides[get_settings] = lambda: Settings()
        return client

    return _make


def test_get_health_with_no_env_or_credentials_returns_contract_body(make_client):
    response = make_client().get(HEALTH_PATH)

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert isinstance(body["version"], str) and body["version"]
    assert isinstance(body["environment"], str) and body["environment"]


@pytest.mark.parametrize(
    ("variable", "field", "value"),
    [("PDC_ENVIRONMENT", "environment", "dev"), ("PDC_VERSION", "version", "abc1234")],
)
def test_get_health_with_env_override_returns_it(make_client, variable, field, value):
    response = make_client(**{variable: value}).get(HEALTH_PATH)

    assert response.json()[field] == value
