# AWS instance environment

This root module launches one EC2 instance from an AMI entry selected by
`bin/generate-aws-tfvars.py`. The catalog-derived variables identify the image;
launch settings such as instance type, subnet, security groups, key pair, and
instance profile are supplied separately.

Use [`bin/terraform-aws.py`](../../bin/terraform-aws.py) to run plans and
applies. It reads the AWS bootstrap key from Vault and supplies temporary STS
credentials to Terraform through the process environment. The provider region
comes from the selected catalog image. The catalog's `image_project` is kept as
image-owner metadata; it does not restrict the AWS account used to launch the
instance. See [`doc/vault-aws.md`](../../doc/vault-aws.md) for setup.

Terraform's local state file lives at `inventory/aws/terraform.tfstate`, beside
the generated tfvars and outside the source tree. Back up that state with the
local inventory it belongs to. See [`doc/state-management.md`](../../doc/state-management.md)
for named workspaces and external state backups.

From the repository root, install the AWS helper dependency into `~/.dib7`:

```bash
~/.dib7/bin/python -m pip install -r requirements.txt
```

Set `AWS_TARGET_PROJECT` to the intended AWS account ID. Then initialize and plan with the generated file:

```bash
~/.dib7/bin/python bin/terraform-aws.py init
~/.dib7/bin/python bin/terraform-aws.py plan \
  -var-file=../../inventory/aws/ubuntu26041-base-project-${AWS_TARGET_PROJECT}.tfvars \
  -var='instance_name=ubuntu26041-test' \
  -var='instance_type=t3.small'
```

Set `subnet_id` and `vpc_security_group_ids` to select an explicit network.
Without them, AWS selects the default network where available. In this AWS
account, the default security group only allows inbound traffic from other
instances using that same group; it does not permit public SSH. For SSH access,
use a subnet with a public IP and internet-gateway route, a security group that
allows TCP port 22 from your client CIDR, and an EC2 key pair you have the
private key for. If the catalog provides `image_ssh_username` and `key_name` is
omitted, Terraform uses that username as the EC2 key pair name by convention;
the pair must exist in the target AWS account and region. Set `key_name`
explicitly in the launch settings to override the convention. Run `apply` only
after reviewing the plan.

For repeatable launch settings, store them in a second ignored tfvars file
under `inventory/aws/`, separate from the catalog-generated file. For example,
`inventory/aws/ubuntu26041-test.settings.tfvars` can contain:

```hcl
instance_name          = "ubuntu26041-test"
instance_type          = "t3.small"
subnet_id              = "subnet-REPLACE_ME"
vpc_security_group_ids = ["sg-REPLACE_ME"]
key_name               = "REPLACE_ME"
associate_public_ip_address = true
```

Pass both files to Terraform with `-var-file`. The launch settings can also be
provided as individual `-var` arguments when running a one-off plan.
