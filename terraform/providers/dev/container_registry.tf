module "container_registry" {
  source        = "../../modules/container_registry"
  name          = var.name
  region        = var.region
  environment   = var.environment
  owner         = var.owner
  backup_region = var.backup_region
}
