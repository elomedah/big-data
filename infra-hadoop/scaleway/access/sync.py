"""Installed on the bastion controller. Fetch data only, never remote playbooks."""
import argparse
import base64
import fcntl
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

import yaml

from validate import load_keys, SCHOOLS, school_keys_path


def synchronize(config):
    project = Path(config["ansible_dir"])
    selected_school = config.get("student_school")
    if selected_school not in SCHOOLS:
        raise ValueError("Configure student_school as ensitech, iris or efrei")
    target = project / "group_vars" / ("student_ssh_keys_" + selected_school + ".yml")
    state = Path(config["state_dir"]) / selected_school
    state.mkdir(parents=True, exist_ok=True)
    with (state / "sync.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        repo = config["repository"]
        headers = {"User-Agent": "student-access-sync", "Accept": "application/vnd.github+json"}
        if config.get("token_file"):
            headers["Authorization"] = "Bearer " + Path(config["token_file"]).read_text().strip()

        def fetch(path):
            with urlopen(Request("https://api.github.com/repos/" + repo + path, headers=headers), timeout=30) as response:
                return response.read()

        commit = json.loads(fetch("/commits/" + quote(config["branch"], safe="")))["sha"]
        document = json.loads(fetch("/contents/" + school_keys_path(selected_school) + "?ref=" + commit))
        raw = base64.b64decode(document["content"])
        with tempfile.TemporaryDirectory(dir=state) as directory:
            incoming = Path(directory) / "keys.yml"
            incoming.write_bytes(raw)
            desired = load_keys(incoming)
        # Retain omitted accounts, but incoming entries replace their key lists.
        previous_path = state / "applied.yml"
        # Include accounts provisioned during a previous partially failed run.
        previous = load_keys(previous_path) if previous_path.exists() else {}
        previous.update(load_keys(target))
        for name, keys in previous.items():
            desired.setdefault(name, keys)
        # Check the merged data too (e.g. a key reassigned to another account).
        with tempfile.TemporaryDirectory(dir=state) as directory:
            merged = Path(directory) / "keys.yml"
            merged.write_text(yaml.safe_dump({"student_ssh_keys": desired}), encoding="utf-8")
            load_keys(merged)
        serialized = yaml.safe_dump({"student_ssh_keys": desired}, sort_keys=True).encode()
        # Force one apply when upgrading from the former append-only behavior.
        digest = hashlib.sha256(b"replace-keys-v1\n" + serialized).hexdigest()
        marker = state / "applied.sha256"
        if marker.exists() and marker.read_text() == digest and target.read_bytes() == serialized:
            print(f"Already synchronized ({commit[:12]})", flush=True)
            return
        # Keep the original file for recovery before the first synchronization.
        backup = state / "initial-keys.yml"
        if not backup.exists():
            backup.write_bytes(target.read_bytes())
        temporary = target.with_suffix(".pending")
        temporary.write_bytes(serialized)
        os.replace(temporary, target)
        print(f"Applying student access from {commit}", flush=True)
        subprocess.run([config.get("ansible_playbook", "ansible-playbook"), "site.yml", "--tags", "students",
                        "-e", "student_school=" + selected_school], cwd=project, check=True, timeout=900)
        # Only record success after Ansible succeeds; failures retry next timer tick.
        pending_state = state / "applied.pending"
        pending_state.write_bytes(serialized)
        os.replace(pending_state, previous_path)
        pending_marker = state / "sha256.pending"
        pending_marker.write_text(digest)
        os.replace(pending_marker, marker)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    args = parser.parse_args()
    synchronize(json.loads(Path(args.config).read_text()))
