import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parents[2] / "web" / "staticwebapp.config.json"


def load_config():
    return json.loads(CONFIG_PATH.read_text())


def test_static_web_app_config_declares_python_runtime():
    assert load_config()["platform"]["apiRuntime"] == "python:3.11"


def test_static_web_app_config_sends_security_headers():
    headers = load_config()["globalHeaders"]

    assert headers["X-Content-Type-Options"] == "nosniff"
    csp = headers["Content-Security-Policy"]
    assert "script-src 'self';" in csp
    assert "style-src 'self';" in csp
    assert "img-src 'self' https://*.blob.core.windows.net;" in csp
    assert "connect-src 'self' https://*.blob.core.windows.net;" in csp


def test_static_web_app_config_does_not_rewrite_api_paths():
    fallback = load_config()["navigationFallback"]

    assert fallback["rewrite"] == "/index.html"
    assert "/api/*" in fallback["exclude"]
