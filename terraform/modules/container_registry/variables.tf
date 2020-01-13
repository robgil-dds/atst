variable "region" {
  type        = string
  description = "Region this module and resources will be created in"
}

variable "name" {
  type        = string
  description = "Unique name for the services in this module"
}

variable "environment" {
  type        = string
  description = "Environment these resources reside (prod, dev, staging, etc)"
}

variable "owner" {
  type        = string
  description = "Owner of the environment and resources created in this module"
}

variable "backup_region" {
  type        = string
  description = "Backup region for georeplicating the container registry"
}

variable "sku" {
  type        = string
  description = "SKU to use for the container registry service"
  default     = "Premium"
}

variable "admin_enabled" {
  type        = string
  description = "Admin enabled? (true/false default: false)"
  default     = false

}
