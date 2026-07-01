#!/usr/bin/env bash
set -euo pipefail

KEY_PATH="${1:-$HOME/.ssh/m2-hadoop-scaleway}"
REMOTE_KEY_PATH="${2:-.ssh/m2-hadoop-scaleway}"
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

ssh -i "$KEY_PATH" "${SSH_USER}@${BASTION_IP}" "mkdir -p ~/.ssh && chmod 700 ~/.ssh"
scp -i "$KEY_PATH" "$KEY_PATH" "${SSH_USER}@${BASTION_IP}:${REMOTE_KEY_PATH}"
ssh -i "$KEY_PATH" "${SSH_USER}@${BASTION_IP}" "chmod 600 '${REMOTE_KEY_PATH}'"

echo "Private key copied to ${SSH_USER}@${BASTION_IP}:${REMOTE_KEY_PATH}"
echo "This allows Ansible on the bastion to connect to private cluster nodes."
