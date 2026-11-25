data "azurerm_client_config" "current" {}

locals {
  resource_providers = [
    "Microsoft.Web",
    "Microsoft.DocumentDB",
    "Microsoft.Storage",
    "Microsoft.OperationalInsights",
    "Microsoft.Insights",
    "Microsoft.AlertsManagement",
    "Microsoft.ManagedIdentity",
    "Microsoft.Authorization",
    "Microsoft.Consumption",
  ]

  resource_group_names = toset(["tfstate", "dev", "prod"])
  state_containers     = toset(["dev", "prod"])
}

resource "azurerm_resource_group" "this" {
  for_each = local.resource_group_names

  name     = "rg-${var.prefix}-${each.value}"
  location = var.location
}

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

resource "azurerm_storage_account" "tfstate" {
  #checkov:skip=CKV_AZURE_206:LRS by design, state is versioned
  #checkov:skip=CKV_AZURE_33:No queue service used
  #checkov:skip=CKV_AZURE_59:Public endpoint needed for laptop apply and GitHub-hosted runners; shared keys and anonymous access disabled
  #checkov:skip=CKV2_AZURE_1:No CMK, MVP
  #checkov:skip=CKV2_AZURE_33:No private endpoint, MVP
  name                = "st${var.prefix}tfstate${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.this["tfstate"].name
  location            = azurerm_resource_group.this["tfstate"].location

  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  shared_access_key_enabled       = false
  allow_nested_items_to_be_public = false

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 7
    }
  }
}

resource "azurerm_storage_container" "tfstate" {
  #checkov:skip=CKV2_AZURE_21:No storage logging sink, MVP
  for_each = local.state_containers

  name                  = "tfstate-${each.value}"
  storage_account_id    = azurerm_storage_account.tfstate.id
  container_access_type = "private"

  depends_on = [azurerm_role_assignment.applier_state_blob_contributor]
}
