# 0004. Terraform and GitHub Actions with per-environment OIDC

## Status

Accepted.

## Context

Everything in Azure must be reproducible and deployed only through GitHub Actions. No long-lived Azure secrets should live in GitHub. There are two environments with different risk: dev (free, open) and prod (reviewed).

## Decision

- Infrastructure is Terraform: reusable modules (`infra/modules/*`) and one root per environment (`infra/envs/dev`, `infra/envs/prod`). State lives in a hardened storage account, one container per environment.
- A one-time bootstrap root (`infra/bootstrap`, run from a laptop) creates the resource groups, the state account, the budget and three managed identities federated with GitHub OIDC: `ci-plan` (read-only, used on pull requests), `deploy-dev` and `deploy-prod`. Each identity is scoped to its own resource group (Contributor for deploy, Reader for plan).
- Workflows log in with `azure/login` and OIDC. No Azure secret exists. Only values such as client ids are repository or environment variables.
- Branch flow: pull requests run `ci.yml` (lint, security, tests, build, Terraform plan). A push to `dev` deploys the `dev` environment. A push to `main` deploys `prod` and needs the approval of required reviewers on the GitHub environment.
- Each deploy applies Terraform, seeds data, uploads to SWA and runs the Bruno smoke. A prod deploy then tags `v<run number>` and stores the artifact `release-v<run number>` for 90 days.
- Two details forced by Azure: the images storage CORS rule is set with `azapi_update_resource`, because `azurerm` would create a dependency cycle between storage and SWA; and the SAS upload flow needs that rule plus a CSP `connect-src` for the blob host.
- Rollback (`rollback.yml`) and destroy (`destroy.yml`) are manual workflows. Destroy needs a typed confirmation.

## Consequences

- No secrets to rotate for Azure access. A compromised dev workflow cannot touch prod resources.
- Every change is reviewed in a pull request, and the plan is visible before merge.
- The bootstrap stack is a manual, local step and its state is local. It is destroyed from a laptop at the end.
- Running Terraform apply on every deploy is slower than a code-only upload, but keeps infrastructure and code in step.

## Alternatives

| Option | Why not |
| --- | --- |
| Service principal secret in GitHub | Long-lived credential that can leak and must be rotated. |
| One shared identity for both environments | A dev workflow could change prod. |
| Bicep or ARM | Azure-only. Terraform gives a reviewable plan in pull requests and an `azapi` escape hatch. |
| Manual deploys from the portal or CLI | Not reproducible and not reviewable. |
