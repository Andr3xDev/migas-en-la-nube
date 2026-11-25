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

Placeholder: commands are finalized in PR 002 (API skeleton).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn function_app:app --app-dir api --reload
curl http://localhost:8000/api/health
```
