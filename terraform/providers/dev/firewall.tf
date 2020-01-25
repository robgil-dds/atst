module "firewall" {
  source                  = "../../modules/firewall"
  owner                   = var.owner
  environment             = var.environment
  region                  = var.region
  name                    = var.name
  resource_group_name     = module.vpc.resource_group_name
  resource_group_location = module.vpc.resource_group_location
  subnet_id               = module.vpc.subnet_list["public"].id
}
