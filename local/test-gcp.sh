#!/bin/bash
# local/test-gcp.sh
# vim: set tabstop=4 shiftwidth=4 expandtab:

set -euo pipefail

# Local cloud smoke test. Set SSH_TARGET to connect and
# DESTROY_AFTER_TEST=1 to destroy the instance after the test.
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null && pwd -P)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." >/dev/null && pwd -P)"
cd "$REPO_ROOT"

PYTHON_BIN=${PYTHON_BIN:-python3}
: "${GCP_TARGET_PROJECT:?Set GCP_TARGET_PROJECT to the target GCP project ID}"
GCP_DEFAULT_ZONE=${GCP_DEFAULT_ZONE:-us-central1-a}
IMAGE=${IMAGE:-ubuntu26041-base}
DESTROY_AFTER_TEST=${DESTROY_AFTER_TEST:-0}
SSH_TARGET=${SSH_TARGET:-}
SSH_USER=${SSH_USER:-ubuntu}
SSH_KEY=${SSH_KEY:-$HOME/.ssh/cloud}
VARSFILE="../../inventory/gcp/$IMAGE-project-$GCP_TARGET_PROJECT.tfvars"
DEPLOYMENT_WORKSPACE=${DEPLOYMENT_WORKSPACE:-gcp-$GCP_TARGET_PROJECT-$GCP_DEFAULT_ZONE-$IMAGE}

if [[ $DESTROY_AFTER_TEST != 0 && $DESTROY_AFTER_TEST != 1 ]] ; then
    echo "DESTROY_AFTER_TEST must be 0 or 1" >&2
    exit 2
fi

"$PYTHON_BIN" bin/generate-gcp-tfvars.py "$IMAGE" --project "$GCP_TARGET_PROJECT"

"$PYTHON_BIN" bin/terraform-gcp.py init -reconfigure

"$PYTHON_BIN" bin/terraform-gcp.py workspace select -or-create "$DEPLOYMENT_WORKSPACE"

"$PYTHON_BIN" bin/terraform-gcp.py --target-project="$GCP_TARGET_PROJECT" plan \
    -var-file="$VARSFILE" -var="zone=$GCP_DEFAULT_ZONE"

"$PYTHON_BIN" bin/terraform-gcp.py --target-project="$GCP_TARGET_PROJECT" apply \
    -var-file="$VARSFILE" -var="zone=$GCP_DEFAULT_ZONE"

if [[ -n $SSH_TARGET ]] ; then
    ssh -i "$SSH_KEY" "$SSH_USER@$SSH_TARGET"
fi

if [[ $DESTROY_AFTER_TEST == 1 ]] ; then
    "$PYTHON_BIN" bin/terraform-gcp.py --target-project="$GCP_TARGET_PROJECT" destroy \
        -var-file="$VARSFILE" -var="zone=$GCP_DEFAULT_ZONE"
fi
