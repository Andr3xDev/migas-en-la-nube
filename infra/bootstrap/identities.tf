locals {
  identity_subjects = {
    ci-plan     = "pull_request"
    deploy-dev  = "environment:dev"
    deploy-prod = "environment:prod"
  }
}

resource "azurerm_user_assigned_identity" "this" {
  for_each = local.identity_subjects

  name                = "id-${var.prefix}-${each.key}"
  resource_group_name = azurerm_resource_group.this["tfstate"].name
  location            = azurerm_resource_group.this["tfstate"].location
}

resource "azurerm_federated_identity_credential" "this" {
  for_each = local.identity_subjects

  name                = "github-${each.key}"
  resource_group_name = azurerm_resource_group.this["tfstate"].name
  parent_id           = azurerm_user_assigned_identity.this[each.key].id
  issuer              = "https://token.actions.githubusercontent.com"
  audience            = ["api://AzureADTokenExchange"]
  subject             = "repo:${var.repo}:${each.value}"
}
