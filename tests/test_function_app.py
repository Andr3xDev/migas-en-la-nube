import azure.functions as func

import function_app


def test_function_app_exposes_anonymous_asgi_app():
    assert isinstance(function_app.app, func.AsgiFunctionApp)
    assert function_app.app.auth_level == func.AuthLevel.ANONYMOUS
