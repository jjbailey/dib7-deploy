#!/bin/bash
# local/test-vsphere.sh
# vim: set tabstop=4 shiftwidth=4 expandtab:

set -euo pipefail

# Local cloud smoke test. Set SSH_TARGET to connect and
# DESTROY_AFTER_TEST=1 to destroy the VM after the test.
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null && pwd -P)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." >/dev/null && pwd -P)"
cd "$REPO_ROOT"

PYTHON_BIN=${PYTHON_BIN:-python3}
CONTENT_LIBRARY=${CONTENT_LIBRARY:-Content_Library}
VSPHERE_CATALOG_VCENTER=${VSPHERE_CATALOG_VCENTER:-legacy}
IMAGE=${IMAGE:-ubuntu26041-base}
DESTROY_AFTER_TEST=${DESTROY_AFTER_TEST:-0}
SSH_TARGET=${SSH_TARGET:-}
SSH_USER=${SSH_USER:-ubuntu}
SSH_KEY=${SSH_KEY:-$HOME/.ssh/cloud}
VARSFILE="../../inventory/vsphere/$IMAGE-$CONTENT_LIBRARY.tfvars"
SETTINGSFILE="../../inventory/vsphere/$IMAGE-launch.settings.tfvars"
DEPLOYMENT_WORKSPACE=${DEPLOYMENT_WORKSPACE:-vsphere-$VSPHERE_CATALOG_VCENTER-$CONTENT_LIBRARY-$IMAGE}
RUNNER_ARGS=()
if [[ -n ${VSPHERE_TARGET_VCENTER:-} ]] ; then
    RUNNER_ARGS=(--target-vcenter "$VSPHERE_TARGET_VCENTER")
fi

if [[ $DESTROY_AFTER_TEST != 0 && $DESTROY_AFTER_TEST != 1 ]] ; then
    echo "DESTROY_AFTER_TEST must be 0 or 1" >&2
    exit 2
fi

"$PYTHON_BIN" bin/generate-vsphere-tfvars.py "$IMAGE" \
    --scope "vcenter=$VSPHERE_CATALOG_VCENTER" \
    --scope "content_library=$CONTENT_LIBRARY"

"$PYTHON_BIN" bin/terraform-vsphere.py init -reconfigure

"$PYTHON_BIN" bin/terraform-vsphere.py "${RUNNER_ARGS[@]}" \
    workspace select -or-create "$DEPLOYMENT_WORKSPACE"

"$PYTHON_BIN" bin/terraform-vsphere.py "${RUNNER_ARGS[@]}" plan \
    -var-file="$VARSFILE" -var-file="$SETTINGSFILE"

"$PYTHON_BIN" bin/terraform-vsphere.py "${RUNNER_ARGS[@]}" apply \
    -var-file="$VARSFILE" -var-file="$SETTINGSFILE"

if [[ -n $SSH_TARGET ]] ; then
    ssh -i "$SSH_KEY" "$SSH_USER@$SSH_TARGET"
fi

if [[ $DESTROY_AFTER_TEST == 1 ]] ; then
    "$PYTHON_BIN" bin/terraform-vsphere.py "${RUNNER_ARGS[@]}" destroy \
        -var-file="$VARSFILE" -var-file="$SETTINGSFILE"
fi
