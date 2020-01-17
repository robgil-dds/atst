variable "environment" {
  default = "dev"
}

variable "region" {
  default = "eastus2"

}

variable "backup_region" {
  default = "westus2"
}


variable "owner" {
  default = "dev"
}

variable "name" {
  default = "cloudzero"
}

variable "virtual_network" {
  type    = string
  default = "10.1.0.0/16"
}


variable "networks" {
  type = map
  default = {
    #format
    #name         = "CIDR, route table, Security Group Name"
    public  = "10.1.1.0/24,public"  # LBs
    private = "10.1.2.0/24,private" # k8s, postgres, redis, dns, ad
  }
}

variable "gateway_subnet" {
  type    = string
  default = "10.1.20.0/24"
}


variable "route_tables" {
  description = "Route tables and their default routes"
  type        = map
  default = {
    public  = "Internet"
    private = "Internet"
    #private = "VnetLocal"
  }
}

variable "dns_servers" {
  type    = list
  default = []
}

variable "k8s_node_size" {
  type    = string
  default = "Standard_A1_v2"
}

variable "k8s_dns_prefix" {
  type    = string
  default = "atat"
}

variable "tenant_id" {
  type    = string
  default = "b5ab0e1e-09f8-4258-afb7-fb17654bc5b3"
}

variable "admin_users" {
  type = map
  default = {
    "Rob Gil"         = "2ca63d41-d058-4e06-aef6-eb517a53b631"
    "Daniel Corrigan" = "d5bb69c2-3b88-4e96-b1a2-320400f1bf1b"
  }
}
