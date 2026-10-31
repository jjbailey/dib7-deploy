terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  backend "local" {
    path          = "../../inventory/azure/terraform.tfstate"
    workspace_dir = "../../inventory/azure/terraform.tfstate.d"
  }
}
