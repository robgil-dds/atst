resource "azurerm_resource_group" "bucket" {
  name     = "${var.name}-${var.environment}-${var.service_name}"
  location = var.region
}

resource "azurerm_storage_account" "bucket" {
  name                     = var.service_name
  resource_group_name      = azurerm_resource_group.bucket.name
  location                 = azurerm_resource_group.bucket.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_container" "bucket" {
  name                  = "content"
  storage_account_name  = azurerm_storage_account.bucket.name
  container_access_type = var.container_access_type
}
