module "operator_keyvault" {
  source           = "../../modules/keyvault"
  name             = "ops"
  region           = var.region
  owner            = var.owner
  environment      = var.environment
  tenant_id        = var.tenant_id
  principal_id     = ""
  admin_principals = var.admin_users
}
