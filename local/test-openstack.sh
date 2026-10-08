#!/bin/bash
# local/test-openstack.sh
# vim: set tabstop=4 shiftwidth=4 expandtab:

set -euo pipefail

# Local cloud smoke test. Set SSH_TARGET to connect and
# DESTROY_AFTER_TEST=1 to destroy the instance after the test.
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null && pwd -P)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." >/dev/null && pwd -P)"
cd "$REPO_ROOT"

PYTHON_BIN=${PYTHON_BIN:-python3}
: "${OS_TARGET_PROJECT:?Set OS_TARGET_PROJECT to the target OpenStack project ID}"
OS_DEFAULT_REGION=${OS_DEFAULT_REGION:-US-WEST-OR-1}
IMAGE=${IMAGE:-ubuntu26041-base}
DESTROY_AFTER_TEST=${DESTROY_AFTER_TEST:-0}
SSH_TARGET=${SSH_TARGET:-}
SSH_USER=${SSH_USER:-ubuntu}
SSH_KEY=${SSH_KEY:-$HOME/.ssh/cloud}
VARSFILE="../../inventory/openstack/$IMAGE-project-$OS_TARGET_PROJECT.tfvars"
SETTINGSFILE="../../inventory/openstack/$IMAGE-launch.settings.tfvars"
DEPLOYMENT_WORKSPACE=${DEPLOYMENT_WORKSPACE:-openstack-$OS_TARGET_PROJECT-$OS_DEFAULT_REGION-$IMAGE}

if [[ $DESTROY_AFTER_TEST != 0 && $DESTROY_AFTER_TEST != 1 ]] ; then
    echo "DESTROY_AFTER_TEST must be 0 or 1" >&2
    exit 2
fi

"$PYTHON_BIN" bin/generate-openstack-tfvars.py "$IMAGE" \
    --project "$OS_TARGET_PROJECT" --region "$OS_DEFAULT_REGION"

"$PYTHON_BIN" bin/terraform-openstack.py init -reconfigure

"$PYTHON_BIN" bin/terraform-openstack.py workspace select -or-create "$DEPLOYMENT_WORKSPACE"

"$PYTHON_BIN" bin/terraform-openstack.py --target-project="$OS_TARGET_PROJECT" plan \
    -var-file="$VARSFILE" -var-file="$SETTINGSFILE"

"$PYTHON_BIN" bin/terraform-openstack.py --target-project="$OS_TARGET_PROJECT" apply \
    -var-file="$VARSFILE" -var-file="$SETTINGSFILE"

if [[ -n $SSH_TARGET ]] ; then
    ssh -i "$SSH_KEY" "$SSH_USER@$SSH_TARGET"
fi

if [[ $DESTROY_AFTER_TEST == 1 ]] ; then
    "$PYTHON_BIN" bin/terraform-openstack.py --target-project="$OS_TARGET_PROJECT" destroy \
        -var-file="$VARSFILE" -var-file="$SETTINGSFILE"
fi
