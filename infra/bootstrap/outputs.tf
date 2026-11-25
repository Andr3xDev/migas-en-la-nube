output "tenant_id" {
  value = data.azurerm_client_config.current.tenant_id
}

output "subscription_id" {
  value = data.azurerm_client_config.current.subscription_id
}

output "ci_plan_client_id" {
  value = azurerm_user_assigned_identity.this["ci-plan"].client_id
}

output "deploy_dev_client_id" {
  value = azurerm_user_assigned_identity.this["deploy-dev"].client_id
}

output "deploy_prod_client_id" {
  value = azurerm_user_assigned_identity.this["deploy-prod"].client_id
}

output "tfstate_resource_group" {
  value = azurerm_resource_group.this["tfstate"].name
}

output "tfstate_account" {
  value = azurerm_storage_account.tfstate.name
}
