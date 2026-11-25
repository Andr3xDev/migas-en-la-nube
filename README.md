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

## Deploy

`.github/workflows/deploy.yml` deploys on push:

| Branch | GitHub environment | Approval |
| --- | --- | --- |
| `dev` | `dev` | none |
| `main` | `prod` | required reviewers |

Each run builds the artifacts, applies Terraform for the environment, deploys `web/` and `api/` to Static Web Apps, then runs `smoke/health.sh <url> <environment>` (up to 12 attempts, 10 s apart) against `/api/health`. After a successful `prod` deploy and smoke, the `release` job tags the commit `v<run number>` and stores the artifacts as `release-v<run number>` for 90 days.

Fallback: if managed Static Web Apps rejects Python 3.11 or the ASGI app, move the API to a linked Function App before continuing.
