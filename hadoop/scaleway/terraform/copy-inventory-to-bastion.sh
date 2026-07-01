#!/usr/bin/env bash
set -euo pipefail

KEY_PATH="${1:-$HOME/.ssh/m2-hadoop-scaleway}"
REMOTE_DIR="${2:-hadoop/scaleway/ansible}"
SSH_USER="${SSH_USER:-ubuntu}"
LOCAL_INVENTORY="../ansible/inventory-bastion.ini"

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

ssh -i "$KEY_PATH" "${SSH_USER}@${BASTION_IP}" "mkdir -p '$REMOTE_DIR'"
scp -i "$KEY_PATH" "$LOCAL_INVENTORY" "${SSH_USER}@${BASTION_IP}:${REMOTE_DIR}/inventory.ini"

echo "Inventory copied to ${SSH_USER}@${BASTION_IP}:${REMOTE_DIR}/inventory.ini"
