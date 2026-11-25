import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "web" / "staticwebapp.config.json"


def test_static_web_app_config_declares_python_runtime():
    config = json.loads(CONFIG_PATH.read_text())

    assert config["platform"]["apiRuntime"] == "python:3.11"
