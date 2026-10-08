terraform {
  required_version = ">= 1.5.0"

  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "~> 3.0"
    }
  }

  backend "local" {
    path          = "../../inventory/openstack/terraform.tfstate"
    workspace_dir = "../../inventory/openstack/terraform.tfstate.d"
  }
}
