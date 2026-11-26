# 0005. Python and FastAPI on Azure Functions

## Status

Accepted.

## Context

The API needs routing, validation, dependency injection and good test support, and it must run as SWA managed Functions (ADR 0001). SWA managed Functions support a limited runtime set.

## Decision

Write the API in Python 3.11 with FastAPI. A single Azure Function (`api/http_app`) uses a catch-all route `{*route}` and hands every request to the FastAPI app through `func.AsgiMiddleware`.

The function uses the v1 programming model (`function.json` plus `__init__.py`). The v2 model with `AsgiFunctionApp` was tried first and failed to deploy on SWA managed Functions, so it is not used.

The code is layered: routes only handle HTTP, services hold rules, ports define repositories, and adapters implement them for Cosmos, Blob and memory.

## Consequences

- Fast tests with `TestClient` and the memory adapters, no Azure needed.
- Validation and OpenAPI come from FastAPI and Pydantic.
- The v1 model is older, but it is what SWA deploys today. The cost is one small entry file.
- Every request goes through the ASGI bridge, which adds a little latency and a cold start.
- If the v2 model starts working on SWA, the entry file can change without touching the app.

## Alternatives

| Option | Why not |
| --- | --- |
| Pure Azure Functions SDK v2 (one function per route) | The `AsgiFunctionApp` form failed to deploy on SWA. Plain v2 triggers would need per-route code and lose FastAPI validation and DI. |
| Java (Functions or Spring) | Heavier build, slower cold starts, more code for the same API. |
| Node.js | Fully viable, but the team knows Python better and the tooling is already set. |
