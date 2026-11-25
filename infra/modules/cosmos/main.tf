locals {
  containers = {
    products = { partition_key = "/category", unique_keys = [] }
    orders   = { partition_key = "/pickupDate", unique_keys = [] }
    users    = { partition_key = "/email", unique_keys = ["/email"] }
  }
}

resource "azurerm_cosmosdb_account" "this" {
  #checkov:skip=CKV_AZURE_140:Managed SWA Functions have no managed identity, so the app authenticates with account keys.
  #checkov:skip=CKV_AZURE_100:Customer-managed keys are out of scope and cost for the MVP; Microsoft-managed encryption applies.
  #checkov:skip=CKV_AZURE_99:Public network access is required; SWA managed Functions have no VNet and the account has no private endpoint.
  #checkov:skip=CKV_AZURE_101:Private endpoints are out of scope for the MVP; no VNet is provisioned.
  #checkov:skip=CKV2_AZURE_22:Customer-managed keys are out of scope for the MVP.
  name                               = var.name
  resource_group_name                = var.resource_group_name
  location                           = var.location
  offer_type                         = "Standard"
  kind                               = "GlobalDocumentDB"
  local_authentication_enabled       = true
  access_key_metadata_writes_enabled = false

  capabilities {
    name = "EnableServerless"
  }

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = var.location
    failover_priority = 0
  }

  backup {
    type = "Continuous"
    tier = "Continuous7Days"
  }
}

resource "azurerm_cosmosdb_sql_database" "this" {
  name                = "migas"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
}

resource "azurerm_cosmosdb_sql_container" "this" {
  for_each = local.containers

  name                  = each.key
  resource_group_name   = var.resource_group_name
  account_name          = azurerm_cosmosdb_account.this.name
  database_name         = azurerm_cosmosdb_sql_database.this.name
  partition_key_paths   = [each.value.partition_key]
  partition_key_version = 2

  dynamic "unique_key" {
    for_each = each.value.unique_keys
    content {
      paths = [unique_key.value]
    }
  }
}
