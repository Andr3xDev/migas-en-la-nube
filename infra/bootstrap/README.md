# Bootstrap

One-time Terraform root, applied locally by the repository owner. It registers the resource providers (through the provider block), creates the resource groups (`rg-<prefix>-tfstate`, `-dev`, `-prod`), the hardened Terraform state storage account, three GitHub-federated managed identities, least-privilege roles and a subscription budget. State is local and gitignored.

"Public access disabled" on the state account means anonymous blob access is off; the network endpoint stays public so the laptop and GitHub-hosted runners can reach it (Entra auth only).

## Prerequisites

- Terraform `>= 1.12, < 2.0`, Azure CLI, GitHub CLI (`gh`) authenticated with permission to set repository variables.
- An Azure user with Owner (or Contributor plus User Access Administrator) on the subscription.

## Apply

```bash
az login
az account set --subscription <subscription-id>

cd infra/bootstrap
cp terraform.tfvars.example terraform.tfvars   # edit repo, github_owner_id, github_repo_id, budget_amount, budget_email
terraform init
terraform apply
```

Get the ids with `gh api repos/<owner>/<name> --jq '.owner.id, .id'` (GitHub OIDC subjects use `owner@owner_id/repo@repo_id`).

If the apply fails with a permission or role error right after creating roles, wait a few minutes and run `terraform apply` again (role propagation delay).

The budget (`budget.tf`) may be rejected on some student subscriptions. If so, delete `budget.tf`, re-run `terraform apply`, and create the budget in the portal instead.

## Repository variables

Run from `infra/bootstrap` after the apply:

```bash
REPO=<owner>/<name>

gh variable set AZURE_TENANT_ID --repo $REPO --body "$(terraform output -raw tenant_id)"
gh variable set AZURE_SUBSCRIPTION_ID --repo $REPO --body "$(terraform output -raw subscription_id)"
gh variable set AZURE_CLIENT_ID_PLAN --repo $REPO --body "$(terraform output -raw ci_plan_client_id)"
gh variable set TFSTATE_RESOURCE_GROUP --repo $REPO --body "$(terraform output -raw tfstate_resource_group)"
gh variable set TFSTATE_ACCOUNT --repo $REPO --body "$(terraform output -raw tfstate_account)"

# Environment variables (create the GitHub environments `dev` and `prod` first)
gh variable set AZURE_CLIENT_ID --repo $REPO --env dev --body "$(terraform output -raw deploy_dev_client_id)"
gh variable set AZURE_CLIENT_ID --repo $REPO --env prod --body "$(terraform output -raw deploy_prod_client_id)"
```

After the first bootstrap apply, run `terraform init` once in `infra/envs/dev` and `infra/envs/prod` as the owner (same `-backend-config` values as CI) so the state blobs exist before the read-only CI plan.

## Destroy

Manual cleanup order:

1. Run the `destroy.yml` workflow (Actions, Run workflow, from `main`) with `environment: prod` and `confirm: prod`, then approve the `prod` environment deployment.
2. Run `destroy.yml` with `environment: dev` and `confirm: dev`.
3. Destroy bootstrap from the laptop:

```bash
cd infra/bootstrap
terraform destroy
```

`destroy.yml` removes only the Terraform-managed resources of its environment; the resource groups stay (bootstrap owns them) until step 3. GitHub environments, their variables and the repository are never removed by any step.

Bootstrap destroy removes the resource groups with everything inside them, the state storage, identities, role assignments and budget. Destroy `infra/envs/dev` and `infra/envs/prod` first so their state is not lost, because their state lives in this storage account. Resource providers are registered by the provider block and stay registered after destroy.
