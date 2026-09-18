"""Validate data before it reaches privileged Ansible tasks. Ed25519 only."""
import argparse
import base64
import json
import re
import struct
from pathlib import Path

import yaml


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise ValueError("Mapping keys must be unique strings")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor("tag:yaml.org,2002:map", unique_mapping)


def login(value):
    # Limit provisioning to student-style names, and reserve service identities.
    reserved = {"root", "ubuntu", "admin", "teacher", "hadoop", "hdfs", "yarn",
                "spark", "hive", "hbase", "ansible", "student", "nobody", "daemon",
                "bin", "sys", "sync", "games", "man", "lp", "mail", "news", "uucp",
                "proxy", "backup", "list", "irc", "sshd", "postgres", "mysql",
                "www-data", "systemd-network", "systemd-timesync", "messagebus"}
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9._-]{0,31}", value) or value in reserved:
        raise ValueError("Invalid or reserved student login")
    return value


def public_key(value):
    if not isinstance(value, str) or len(value) > 1024 or '\n' in value or '\r' in value:
        raise ValueError("Expected one public key per line")
    parts = value.split()
    if len(parts) < 2 or parts[0] != "ssh-ed25519":
        raise ValueError("Only plain ssh-ed25519 public keys are accepted")
    try:
        blob = base64.b64decode(parts[1], validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid public key encoding") from exc
    prefix = struct.pack(">I", 11) + b"ssh-ed25519" + struct.pack(">I", 32)
    if len(blob) != len(prefix) + 32 or not blob.startswith(prefix):
        raise ValueError("Invalid Ed25519 public key structure")
    # Do not copy arbitrary comments/options to the server.
    return "ssh-ed25519 " + base64.b64encode(blob).decode("ascii")


def load_keys(path):
    raw = Path(path).read_text(encoding="utf-8")
    if len(raw) > 1_000_000:
        raise ValueError("Keys file too large")
    data = yaml.load(raw, Loader=UniqueLoader)
    if not isinstance(data, dict) or set(data) != {"student_ssh_keys"}:
        raise ValueError("Only student_ssh_keys is allowed")
    mapping = data["student_ssh_keys"]
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("Expected a non-empty student mapping")
    seen = set()
    result = {}
    for name, keys in mapping.items():
        login(name)
        if not isinstance(keys, list) or len(keys) > 10:
            raise ValueError("Expected at most ten keys per student (or [] to revoke)")
        result[name] = []
        for value in keys:
            key = public_key(value)
            if key in seen:
                raise ValueError("Duplicate key within or across student accounts")
            seen.add(key)
            result[name].append(key)
    return result


def load_roster(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique_json)
    if not isinstance(data, dict) or set(data) != {"github_users"} or not isinstance(data["github_users"], dict):
        raise ValueError("Expected github_users mapping")
    result = {}
    for github, name in data["github_users"].items():
        if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", github):
            raise ValueError("Invalid GitHub username")
        if github.lower() in result or name in result.values():
            raise ValueError("Each GitHub account and student login must be unique")
        result[github.lower()] = login(name)
    return result


def unique_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("keys")
    parser.add_argument("--roster")
    args = parser.parse_args()
    load_keys(args.keys)
    if args.roster:
        load_roster(args.roster)
    print("Student access data is valid")
