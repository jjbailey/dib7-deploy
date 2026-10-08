terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  backend "local" {
    path          = "../../inventory/aws/terraform.tfstate"
    workspace_dir = "../../inventory/aws/terraform.tfstate.d"
  }
}
