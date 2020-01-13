module "task_order_bucket" {
  source       = "../../modules/bucket"
  service_name = "tasksatat"
  owner        = var.owner
  name         = var.name
  environment  = var.environment
  region       = var.region
}
