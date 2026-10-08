# Read the GCP service-account key stored in Vault for this project.
path "secret/data/dib7-deploy/gcp" {
  capabilities = ["read"]
}
