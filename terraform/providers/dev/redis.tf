module "redis" {
  source      = "../../modules/redis"
  owner       = var.owner
  environment = var.environment
  region      = var.region
  name        = var.name
}
