module "k8s" {
  source              = "../../modules/k8s"
  region              = var.region
  name                = var.name
  environment         = var.environment
  owner               = var.owner
  k8s_dns_prefix      = var.k8s_dns_prefix
  k8s_node_size       = var.k8s_node_size
  vnet_subnet_id      = module.vpc.subnets #FIXME - output from module.vpc.subnets should be map
  enable_auto_scaling = true
  max_count           = 5
  min_count           = 3
}

#module "main_lb" {
#  source      = "../../modules/lb"
#  region      = var.region
#  name        = "main-${var.name}"
#  environment = var.environment
#  owner       = var.owner
#}

#module "auth_lb" {
#  source      = "../../modules/lb"
#  region      = var.region
#  name        = "auth-${var.name}"
#  environment = var.environment
#  owner       = var.owner
#}
