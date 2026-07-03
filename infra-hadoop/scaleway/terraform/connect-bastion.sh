#!/usr/bin/env bash
set -euo pipefail

KEY_PATH="${1:-$HOME/.ssh/m2-hadoop-scaleway}"
SSH_USER="${SSH_USER:-ubuntu}"

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

echo "Connecting to bastion: ${SSH_USER}@${BASTION_IP}"
exec ssh -i "$KEY_PATH" "${SSH_USER}@${BASTION_IP}"
