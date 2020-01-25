variable "resource_group_name" {
  description = "Resource group for the VPC"
  type        = string
}

variable "resource_group_location" {
  description = "Resource group location for vpc"
  type        = string
}

variable "environment" {
  description = "Environment (Prod,Dev,etc)"
}

variable "region" {
  description = "Region (useast2, etc)"

}

variable "name" {
  description = "Name or prefix to use for all resources created by this module"
}

variable "owner" {
  description = "Owner of these resources"

}

variable "subnet_id" {
  description = "The public subnet the firewall should reside"
  type        = string

}
