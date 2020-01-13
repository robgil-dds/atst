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

variable "subnet_id" {
  type        = string
  description = "Subnet the SQL server should run"
}

variable "sku_name" {
  type        = string
  description = "SKU name"
  default     = "GP_Gen5_2"
}

variable "sku_capacity" {
  type        = string
  description = "SKU Capacity"
  default     = "2"
}

variable "sku_tier" {
  type        = string
  description = "SKU Tier"
  default     = "GeneralPurpose"

}

variable "sku_family" {
  type        = string
  description = "SKU Family"
  default     = "Gen5"
}

variable "storage_mb" {
  type        = string
  description = "Size in MB of the storage used for the sql server"
  default     = "5120"
}

variable "storage_backup_retention_days" {
  type        = string
  description = "Storage backup retention (days)"
  default     = "7"
}

variable "storage_geo_redundant_backup" {
  type        = string
  description = "Geographic redundant backup (Enabled/Disabled)"
  default     = "Disabled"
}

variable "storage_auto_grow" {
  type        = string
  description = "Auto Grow? (Enabled/Disabled)"
  default     = "Enabled"
}

variable "administrator_login" {
  type        = string
  description = "Administrator login"
  default     = "atat_master" # FIXME - Remove with wrapper using KeyVault
}

variable "administrator_login_password" {
  type        = string
  description = "Administrator password"
  default     = "eI0l7yswwtuhHpwzoVjwRKdAcuGNsg" # FIXME - Remove with wrapper using KeyVault
}

variable "postgres_version" {
  type        = string
  description = "Postgres version to use"
  default     = "10"
}

variable "ssl_enforcement" {
  type        = string
  description = "Enforce SSL (Enabled/Disable)"
  default     = "Enabled"
}

