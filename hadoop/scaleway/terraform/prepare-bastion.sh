#!/usr/bin/env bash
set -euo pipefail

KEY_PATH="${1:-$HOME/.ssh/m2-hadoop-scaleway}"
REMOTE_PROJECT_DIR="${2:-hadoop/scaleway}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/copy-inventory-to-bastion.sh" "$KEY_PATH" "$REMOTE_PROJECT_DIR"
"$SCRIPT_DIR/copy-private-key-to-bastion.sh" "$KEY_PATH"

echo
echo "Bastion is prepared."
echo "Connect with:"
echo "  $SCRIPT_DIR/connect-bastion.sh $KEY_PATH"
echo
echo "Then run on the bastion:"
echo "  cd $REMOTE_PROJECT_DIR/ansible"
echo "  ansible-galaxy collection install -r requirements.yml"
echo "  ansible-playbook site.yml"
