resource "azurerm_role_assignment" "applier_state_blob_contributor" {
  scope                = azurerm_storage_account.tfstate.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "ci_plan_reader" {
  for_each = local.state_containers

  scope                = azurerm_resource_group.this[each.value].id
  role_definition_name = "Reader"
  principal_id         = azurerm_user_assigned_identity.this["ci-plan"].principal_id
}

resource "azurerm_role_assignment" "ci_plan_state_blob_reader" {
  scope                = azurerm_storage_account.tfstate.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.this["ci-plan"].principal_id
}

resource "azurerm_role_assignment" "deploy_contributor" {
  for_each = local.state_containers

  scope                = azurerm_resource_group.this[each.value].id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.this["deploy-${each.value}"].principal_id
}

resource "azurerm_role_assignment" "deploy_state_blob_contributor" {
  for_each = local.state_containers

  scope                = azurerm_storage_container.tfstate[each.value].resource_manager_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.this["deploy-${each.value}"].principal_id
}
