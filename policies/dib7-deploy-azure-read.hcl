# Read the Azure service principal stored in Vault for this project.
path "secret/data/dib7-deploy/azure" {
  capabilities = ["read"]
}
