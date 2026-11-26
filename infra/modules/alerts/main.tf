resource "azurerm_monitor_action_group" "this" {
  name                = "ag-${var.name}"
  resource_group_name = var.resource_group_name
  short_name          = "pdc-alerts"

  email_receiver {
    name                    = "operator"
    email_address           = var.alert_email
    use_common_alert_schema = true
  }
}

resource "azurerm_application_insights_standard_web_test" "health" {
  name                    = "avail-${var.name}-health"
  resource_group_name     = var.resource_group_name
  location                = var.location
  application_insights_id = var.app_insights_id
  frequency               = 900
  geo_locations           = ["us-tx-sn1-azr", "us-il-ch1-azr"]
  retry_enabled           = true

  request {
    url = "https://${var.probe_url}"
  }

  validation_rules {
    expected_status_code = 200
  }

  # Links the test to the Availability blade of the component.
  tags = {
    "hidden-link:${var.app_insights_id}" = "Resource"
  }
}

resource "azurerm_monitor_metric_alert" "availability" {
  name                = "alert-${var.name}-availability"
  resource_group_name = var.resource_group_name
  description         = "Health probe failed from both locations."
  scopes              = [azurerm_application_insights_standard_web_test.health.id, var.app_insights_id]
  severity            = 1
  # Probe runs every 900 s per location; the window spans at least two runs.
  frequency   = "PT5M"
  window_size = "PT30M"

  application_insights_web_test_location_availability_criteria {
    web_test_id           = azurerm_application_insights_standard_web_test.health.id
    component_id          = var.app_insights_id
    failed_location_count = 2
  }

  action {
    action_group_id = azurerm_monitor_action_group.this.id
  }
}

resource "azurerm_monitor_metric_alert" "traffic_spike" {
  name                = "alert-${var.name}-traffic"
  resource_group_name = var.resource_group_name
  description         = "More than ${var.traffic_spike_threshold} API requests in the evaluation window."
  scopes              = [var.app_insights_id]
  # Informational notice (traffic above design), not a failure.
  severity    = 3
  frequency   = var.traffic_spike_frequency
  window_size = var.traffic_spike_window

  criteria {
    metric_namespace = "microsoft.insights/components"
    metric_name      = "requests/count"
    aggregation      = "Count"
    operator         = "GreaterThan"
    threshold        = var.traffic_spike_threshold
  }

  action {
    action_group_id = azurerm_monitor_action_group.this.id
  }
}

resource "azurerm_monitor_metric_alert" "server_errors" {
  name                = "alert-${var.name}-5xx"
  resource_group_name = var.resource_group_name
  description         = "More than 5 failed requests with a 5xx status in 15 minutes."
  scopes              = [var.app_insights_id]
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "microsoft.insights/components"
    metric_name      = "requests/failed"
    aggregation      = "Count"
    operator         = "GreaterThan"
    threshold        = 5

    dimension {
      name     = "request/resultCode"
      operator = "StartsWith"
      values   = ["5"]
    }
  }

  action {
    action_group_id = azurerm_monitor_action_group.this.id
  }
}
