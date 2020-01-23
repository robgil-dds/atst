module "task_order_bucket" {
  source       = "../../modules/bucket"
  service_name = "jeditasksatat"
  owner        = var.owner
  name         = var.name
  environment  = var.environment
  region       = var.region
  policy       = "Deny"
  subnet_ids   = [module.vpc.subnets]
}

module "tf_state" {
  source       = "../../modules/bucket"
  service_name = "jedidevtfstate"
  owner        = var.owner
  name         = var.name
  environment  = var.environment
  region       = var.region
  policy       = "Allow"
  subnet_ids   = []
}
