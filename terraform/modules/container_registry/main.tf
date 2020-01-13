resource "azurerm_resource_group" "acr" {
  name     = "${var.name}-${var.environment}-acr"
  location = var.region
}

resource "azurerm_container_registry" "acr" {
  name                = "${var.name}${var.environment}registry" # Alpha Numeric Only
  resource_group_name = azurerm_resource_group.acr.name
  location            = azurerm_resource_group.acr.location
  sku                 = var.sku
  admin_enabled       = var.admin_enabled
  #georeplication_locations = [azurerm_resource_group.acr.location, var.backup_region]
}