# Allow the operator sync command to mirror dib7's encrypted provider data.
path "secret/data/dib7-deploy/aws" {
  capabilities = ["create", "update"]
}

path "secret/data/dib7-deploy/gcp" {
  capabilities = ["create", "update"]
}

path "secret/data/dib7-deploy/openstack" {
  capabilities = ["create", "update"]
}

path "secret/data/dib7-deploy/vsphere" {
  capabilities = ["create", "update"]
}
