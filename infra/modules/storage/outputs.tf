output "account_name" {
  value = azurerm_storage_account.this.name
}

output "account_id" {
  value = azurerm_storage_account.this.id
}

output "connection_string" {
  value     = azurerm_storage_account.this.primary_connection_string
  sensitive = true
}

output "images_container_url" {
  value = "${azurerm_storage_account.this.primary_blob_endpoint}${azurerm_storage_container.images.name}"
}
