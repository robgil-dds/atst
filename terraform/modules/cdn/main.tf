resource "random_id" "server" {
  keepers = {
    azi_id = 1
  }

  byte_length = 8
}

resource "azurerm_resource_group" "cdn" {
  name     = "${var.name}-${var.environment}-cdn"
  location = var.region
}

resource "azurerm_cdn_profile" "cdn" {
  name                = "${var.name}-${var.environment}-profile"
  location            = azurerm_resource_group.cdn.location
  resource_group_name = azurerm_resource_group.cdn.name
  sku                 = var.sku
}

resource "azurerm_cdn_endpoint" "cdn" {
  name                = "${var.name}-${var.environment}-${random_id.server.hex}"
  profile_name        = azurerm_cdn_profile.cdn.name
  location            = azurerm_resource_group.cdn.location
  resource_group_name = azurerm_resource_group.cdn.name

  origin {
    name      = "${var.name}-${var.environment}-origin"
    host_name = var.origin_host_name
  }
}
