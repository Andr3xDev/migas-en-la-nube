# 0001. Serverless with Static Web Apps and managed Functions

## Status

Accepted.

## Context

Migas en la Nube is a small bakery shop: low and bursty traffic, one developer, a student Azure subscription with a budget. The system must be cheap when idle, deployable only from GitHub Actions and easy to destroy.

## Decision

Host the static front end and the API on Azure Static Web Apps (SWA). The API is a FastAPI app running as SWA managed Functions behind the same host, so the browser calls `/api/*` on its own origin (no CORS for the API). Dev uses the Free tier and prod uses Standard.

## Consequences

- No servers, no containers and no scaling configuration. Idle cost is close to zero.
- One host per environment, one deploy action (`Azure/static-web-apps-deploy`) for both web and API.
- Managed Functions have limits: the v1 programming model is required (see ADR 0005), and SWA overwrites the `Authorization` header (see ADR 0003).
- Cold starts exist and are accepted.
- Rollback is a redeploy of a stored artifact, with no infrastructure change.

## Alternatives

| Option | Why not |
| --- | --- |
| App Service plan | Fixed monthly cost even when idle. More to patch and configure for the same traffic. |
| Containers (Container Apps, AKS) | Needs an image build, a registry and more infrastructure code than the project justifies. |
| Linked Function App | Works, but adds a second resource, CORS and a second deploy path. Kept only as a fallback if managed Functions stopped working. |
