# bin/terraform-azure.py supplies the subscription and service principal
# through ARM_* environment variables read from Vault.
provider "azurerm" {
  features {}

  # Do not register dozens of unrelated resource providers on first use.
  # Microsoft.Compute and Microsoft.Network are registered once per
  # subscription; see doc/vault-azure.md.
  resource_provider_registrations = "none"
}
