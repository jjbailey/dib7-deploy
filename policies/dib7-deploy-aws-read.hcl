# Read only the AWS bootstrap credential stored in Vault for this project.
path "secret/data/dib7-deploy/aws" {
  capabilities = ["read"]
}
