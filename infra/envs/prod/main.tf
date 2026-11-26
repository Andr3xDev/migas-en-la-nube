locals {
  environment = "prod"
  sku_tier    = "Standard"
  name        = "${var.prefix}-${local.environment}"
}

data "azurerm_resource_group" "this" {
  name = "rg-${var.prefix}-${local.environment}"
}

resource "random_string" "suffix" {
  length  = 6
  lower   = true
  upper   = false
  numeric = true
  special = false
}

resource "random_password" "jwt_key" {
  length  = 48
  special = false
}

module "observability" {
  source = "../../modules/observability"

  name                = local.name
  resource_group_name = data.azurerm_resource_group.this.name
  location            = data.azurerm_resource_group.this.location
}

module "cosmos" {
  source = "../../modules/cosmos"

  name                = "cosmos-${local.name}-${random_string.suffix.result}"
  resource_group_name = data.azurerm_resource_group.this.name
  location            = data.azurerm_resource_group.this.location
}

module "storage" {
  source = "../../modules/storage"

  name                = "st${var.prefix}${local.environment}${random_string.suffix.result}"
  resource_group_name = data.azurerm_resource_group.this.name
  location            = data.azurerm_resource_group.this.location
}

module "static_web_app" {
  source = "../../modules/static_web_app"

  name                = "swa-${local.name}"
  resource_group_name = data.azurerm_resource_group.this.name
  location            = data.azurerm_resource_group.this.location
  sku_tier            = local.sku_tier

  app_settings = {
    PDC_ENVIRONMENT                       = local.environment
    PDC_VERSION                           = var.app_version
    PDC_JWT_KEY                           = random_password.jwt_key.result
    PDC_COSMOS_CONNECTION_STRING          = module.cosmos.connection_string
    PDC_STORAGE_CONNECTION_STRING         = module.storage.connection_string
    PDC_IMAGES_CONTAINER_URL              = module.storage.images_container_url
    APPLICATIONINSIGHTS_CONNECTION_STRING = module.observability.app_insights_connection_string
  }
}

module "alerts" {
  source = "../../modules/alerts"

  name                = local.name
  resource_group_name = data.azurerm_resource_group.this.name
  location            = data.azurerm_resource_group.this.location
  app_insights_id     = module.observability.app_insights_id
  probe_url           = "${module.static_web_app.default_host_name}/api/health"
  alert_email         = var.alert_email
}

resource "azapi_update_resource" "images_cors" {
  type        = "Microsoft.Storage/storageAccounts/blobServices@2023-05-01"
  resource_id = "${module.storage.account_id}/blobServices/default"

  body = {
    properties = {
      cors = {
        corsRules = [{
          allowedOrigins  = ["https://${module.static_web_app.default_host_name}"]
          allowedMethods  = ["PUT"]
          allowedHeaders  = ["*"]
          exposedHeaders  = []
          maxAgeInSeconds = 3600
        }]
      }
    }
  }
}
