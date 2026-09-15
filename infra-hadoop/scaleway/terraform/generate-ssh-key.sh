#!/usr/bin/env bash
set -euo pipefail

KEY_PATH="${1:-$HOME/.ssh/m2-hadoop-scaleway}"
COMMENT="${2:-m2-hadoop-scaleway}"

if [[ -f "$KEY_PATH" || -f "$KEY_PATH.pub" ]]; then
  echo "SSH key already exists:"
  echo "  $KEY_PATH"
  echo "  $KEY_PATH.pub"
  echo
  echo "Choose another path or remove the existing key first."
  exit 1
fi

mkdir -p "$(dirname "$KEY_PATH")"
chmod 700 "$(dirname "$KEY_PATH")"

ssh-keygen -t ed25519 -a 100 -f "$KEY_PATH" -C "$COMMENT"
chmod 600 "$KEY_PATH"
chmod 644 "$KEY_PATH.pub"

echo
echo "SSH key generated."
echo
echo "Private key:"
echo "  $KEY_PATH"
echo
echo "Public key to put in terraform.tfvars:"
echo
cat "$KEY_PATH.pub"
