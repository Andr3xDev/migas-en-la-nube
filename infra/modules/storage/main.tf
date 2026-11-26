resource "azurerm_storage_account" "this" {
  #checkov:skip=CKV_AZURE_59:Anonymous read on the images container is the product requirement; the account setting enables it.
  #checkov:skip=CKV_AZURE_190:Public blob read on the images container is by design.
  #checkov:skip=CKV_AZURE_33:Queue logging is irrelevant; the account has no queues.
  #checkov:skip=CKV_AZURE_206:LRS is enough for MVP product images; GRS would add cost.
  #checkov:skip=CKV2_AZURE_1:Customer-managed keys are out of scope for the MVP.
  #checkov:skip=CKV2_AZURE_33:Private endpoints are out of scope for the MVP; no VNet is provisioned.
  #checkov:skip=CKV2_AZURE_47:Anonymous blob read is required for the public images container.
  #checkov:skip=CKV2_AZURE_40:Shared key is required to issue SAS tokens for browser uploads; scoped to the images account only.
  name                            = var.name
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = true
  shared_access_key_enabled       = true

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 7
    }
  }

  # App SAS tokens live 5 minutes; "Log" reports longer-lived tokens without blocking them.
  sas_policy {
    expiration_period = "00.01:00:00"
    expiration_action = "Log"
  }

  lifecycle {
    # CORS is managed by azapi_update_resource in the env root (avoids a storage <-> SWA cycle).
    ignore_changes = [blob_properties[0].cors_rule]
  }
}

resource "azurerm_storage_container" "images" {
  #checkov:skip=CKV2_AZURE_21:Blob read logging is out of scope for the MVP.
  #checkov:skip=CKV_AZURE_34:Public blob read on images is by design; no secrets are stored here.
  name                  = "images"
  storage_account_id    = azurerm_storage_account.this.id
  container_access_type = "blob"
}
