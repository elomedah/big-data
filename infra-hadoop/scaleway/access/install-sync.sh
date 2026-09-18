#!/usr/bin/env bash
set -euo pipefail

# Run as the existing Ansible controller user, not root.
if [ "$(id -u)" -eq 0 ]; then
  echo "Run as the bastion Ansible user (normally ubuntu), without sudo." >&2
  exit 1
fi
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANSIBLE_DIR="$(cd "${1:-$SOURCE_DIR/../ansible}" && pwd)"
REPOSITORY="${2:-elomedah/big-data}"
BRANCH="${3:-main}"
INSTALL_DIR="$HOME/.local/share/student-access"
export ANSIBLE_DIR REPOSITORY BRANCH INSTALL_DIR

command -v ansible-playbook >/dev/null
test -f "$ANSIBLE_DIR/inventory.ini"
test -f "$ANSIBLE_DIR/group_vars/student_ssh_keys.yml"
mkdir -p "$INSTALL_DIR" "$HOME/.config/systemd/user"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install -r "$SOURCE_DIR/requirements.txt"
cp "$SOURCE_DIR/validate.py" "$SOURCE_DIR/sync.py" "$INSTALL_DIR/"
python3 - <<'PY'
import json, os
from pathlib import Path
root = Path(os.environ['INSTALL_DIR'])
config = root / 'config.json'
old = json.loads(config.read_text()) if config.exists() else {}
config.write_text(json.dumps({
    'repository': os.environ['REPOSITORY'], 'branch': os.environ['BRANCH'],
    'ansible_dir': os.environ['ANSIBLE_DIR'], 'state_dir': str(root / 'state'),
    'token_file': old.get('token_file', '')}, indent=2) + '\n')
PY
cat > "$HOME/.config/systemd/user/student-access.service" <<'EOF'
[Unit]
Description=Synchronize approved student SSH keys
[Service]
Type=oneshot
Environment="PATH=%h/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart="%h/.local/share/student-access/venv/bin/python" "%h/.local/share/student-access/sync.py" "%h/.local/share/student-access/config.json"
TimeoutStartSec=16min
UMask=0077
EOF
cat > "$HOME/.config/systemd/user/student-access.timer" <<'EOF'
[Unit]
Description=Check approved student SSH keys every two minutes
[Timer]
OnBootSec=1min
OnUnitInactiveSec=2min
[Install]
WantedBy=timers.target
EOF
systemctl --user daemon-reload
echo "Installed. Review $INSTALL_DIR/config.json, then run:"
echo "  systemctl --user start student-access.service"
echo "  journalctl --user -u student-access.service -n 50"
echo "  sudo loginctl enable-linger $(id -un)"
echo "  systemctl --user enable --now student-access.timer"
