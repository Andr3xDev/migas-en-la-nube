# migas-en-la-nube

Pan de la Casa: bakery ordering platform on Azure. This repo starts as a walking skeleton: a FastAPI app on Azure Functions behind Static Web Apps, exposing `GET /api/health`, deployed to Azure only through GitHub Actions, with Terraform managing the infrastructure.

## Layout

| Folder | Purpose |
| --- | --- |
| `api/` | FastAPI app and Azure Functions entry point |
| `web/` | Static web front end |
| `infra/` | Terraform (bootstrap, modules, environments) |
| `tests/` | API tests |
| `smoke/` | Post-deploy smoke tests |
| `docs/` | Documentation |

## Local run

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cd api && uvicorn app.main:app --reload
curl http://localhost:8000/api/health
```

Settings come from `PDC_VERSION` (default `0.1.0`) and `PDC_ENVIRONMENT` (default `local`). Run the tests from the repo root with `pytest --cov`.
