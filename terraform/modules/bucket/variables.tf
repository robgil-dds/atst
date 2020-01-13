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

variable "container_access_type" {
  default     = "private"
  description = "Access type for the container (Default: private)"
  type        = string

}

variable "service_name" {
  description = "Name of the service using this bucket"
  type        = string
}
