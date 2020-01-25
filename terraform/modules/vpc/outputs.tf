output "subnets" {
  value = azurerm_subnet.subnet["private"].id #FIXED: this is now legacy, use subnet_list
}

output "subnet_list" {
  value = {
    for k, id in azurerm_subnet.subnet : k => id
  }
}

output "resource_group_name" {
  value = azurerm_resource_group.vpc.name
}

output "resource_group_location" {
  value = azurerm_resource_group.vpc.location
}