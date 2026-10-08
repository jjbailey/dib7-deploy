terraform {
  required_version = ">= 1.5.0"

  required_providers {
    vsphere = {
      source  = "vmware/vsphere"
      version = "~> 2.17"
    }
  }

  backend "local" {
    path          = "../../inventory/vsphere/terraform.tfstate"
    workspace_dir = "../../inventory/vsphere/terraform.tfstate.d"
  }
}
