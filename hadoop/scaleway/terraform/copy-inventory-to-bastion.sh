#!/usr/bin/env bash
set -euo pipefail

KEY_PATH="${1:-$HOME/.ssh/m2-hadoop-scaleway}"
REMOTE_PROJECT_DIR="${2:-hadoop/scaleway}"
SSH_USER="${SSH_USER:-ubuntu}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCALEWAY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOCAL_INVENTORY="$SCALEWAY_DIR/ansible/inventory-bastion.ini"

if ! command -v terraform >/dev/null 2>&1; then
  echo "terraform command not found. Install Terraform first."
  exit 1
fi

if [[ ! -f "$KEY_PATH" ]]; then
  echo "Private key not found: $KEY_PATH"
  echo "Generate it first with:"
  echo "  ./generate-ssh-key.sh"
  exit 1
fi

BASTION_IP="$(terraform output -raw bastion_public_ip)"

if [[ -z "$BASTION_IP" ]]; then
  echo "Could not read bastion_public_ip from Terraform outputs."
  echo "Run terraform apply first."
  exit 1
fi

terraform output -raw bastion_ansible_inventory > "$LOCAL_INVENTORY"

tar \
  --exclude="terraform/.terraform" \
  --exclude="terraform/terraform.tfstate" \
  --exclude="terraform/terraform.tfstate.backup" \
  --exclude="terraform/terraform.tfvars" \
  -C "$SCALEWAY_DIR" \
  -czf - . | ssh -i "$KEY_PATH" "${SSH_USER}@${BASTION_IP}" \
  "mkdir -p '$REMOTE_PROJECT_DIR' && tar -xzf - -C '$REMOTE_PROJECT_DIR' && cp '$REMOTE_PROJECT_DIR/ansible/inventory-bastion.ini' '$REMOTE_PROJECT_DIR/ansible/inventory.ini'"

echo "Scaleway project copied to ${SSH_USER}@${BASTION_IP}:${REMOTE_PROJECT_DIR}"
echo "Bastion inventory installed at ${REMOTE_PROJECT_DIR}/ansible/inventory.ini"
