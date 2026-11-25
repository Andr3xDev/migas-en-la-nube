locals {
  budget_thresholds = [50, 80, 100]
}

resource "azurerm_consumption_budget_subscription" "this" {
  name            = "budget-${var.prefix}"
  subscription_id = "/subscriptions/${data.azurerm_client_config.current.subscription_id}"
  amount          = var.budget_amount
  time_grain      = "Monthly"

  time_period {
    start_date = formatdate("YYYY-MM-01'T'00:00:00'Z'", timestamp())
  }

  dynamic "notification" {
    for_each = local.budget_thresholds

    content {
      enabled        = true
      threshold      = notification.value
      operator       = "GreaterThanOrEqualTo"
      threshold_type = "Actual"
      contact_emails = [var.budget_email]
    }
  }

  lifecycle {
    # timestamp() changes every run; the budget start date must stay fixed.
    ignore_changes = [time_period]
  }
}
