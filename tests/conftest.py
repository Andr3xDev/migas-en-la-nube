import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    # Imported lazily: test_health purges app.* from sys.modules between tests.
    from app.main import app

    yield TestClient(app)
    app.dependency_overrides.clear()
