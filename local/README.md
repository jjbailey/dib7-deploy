# Local cloud smoke scripts

The `test-*.sh` scripts are manual smoke tests that create real cloud
resources. They run a plan followed by an interactive apply, stop when a command
fails, and leave the instance running by default. They do not contain fixed
repository paths or SSH addresses.

Each script selects a named workspace based on its provider, target, and image
before planning. Set `DEPLOYMENT_WORKSPACE` to override it. Existing resources
in the `default` workspace remain there; set `DEPLOYMENT_WORKSPACE=default` only
when you intend to manage that existing state.

Initialize the provider root before the first run. After a backend
configuration change, run `init -reconfigure` through that provider's wrapper
before rerunning the smoke script; see [state management](../doc/state-management.md).

Set `SSH_TARGET` to connect after apply. `SSH_USER` defaults to `ubuntu` and
`SSH_KEY` defaults to `~/.ssh/cloud`. Set `DESTROY_AFTER_TEST=1` to run an
interactive Terraform destroy after the SSH session ends. Otherwise, destroy
the instance manually when finished. Each script uses the provider's existing
Terraform state under `inventory/`, so check that state and the selected cloud
project before applying or destroying.

The Python executable defaults to `python3`; set `PYTHON_BIN` when the needed
dependencies are installed in another environment. For example:

```bash
PYTHON_BIN="$HOME/.dib7/bin/python" ./local/test-aws.sh
```

Provider-specific selector overrides:

- AWS: `AWS_TARGET_PROJECT`, `AWS_CATALOG_REGION`
- GCP: `GCP_TARGET_PROJECT`, `GCP_DEFAULT_ZONE`
- OpenStack: `OS_TARGET_PROJECT`, `OS_DEFAULT_REGION`
- vSphere: `CONTENT_LIBRARY`, `VSPHERE_CATALOG_VCENTER`, and optionally
  `VSPHERE_TARGET_VCENTER` when the Vault entry needs an explicit selector

The non-cloud unit tests live in `tests/` and can be run with
`python3 -m unittest discover -s tests -v`.
