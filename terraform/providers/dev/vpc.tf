module "vpc" {
  source          = "../../modules/vpc/"
  environment     = var.environment
  region          = var.region
  virtual_network = var.virtual_network
  networks        = var.networks
  gateway_subnet  = var.gateway_subnet
  route_tables    = var.route_tables
  owner           = var.owner
  name            = var.name
  dns_servers     = var.dns_servers
}

