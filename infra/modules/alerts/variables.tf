variable "name" {
  description = "Name suffix shared by the alert resources."
  type        = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "app_insights_id" {
  description = "Application Insights resource the alerts and the availability test attach to."
  type        = string
}

variable "probe_url" {
  description = "Host and path probed by the availability test, without scheme."
  type        = string
}

variable "alert_email" {
  description = "Email address that receives every alert."
  type        = string
}

variable "traffic_spike_threshold" {
  description = "API requests in the window above which the traffic alert fires. About 5x the Saturday peak at 3x."
  type        = number
  default     = 1500
}

variable "traffic_spike_window" {
  description = "Window the traffic alert counts requests over (ISO 8601 duration)."
  type        = string
  default     = "PT5M"
}

variable "traffic_spike_frequency" {
  description = "How often the traffic alert is evaluated (ISO 8601 duration)."
  type        = string
  default     = "PT1M"
}
