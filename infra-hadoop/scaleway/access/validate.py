"""Validate data before it reaches privileged Ansible tasks. Ed25519 only."""
import argparse
import base64
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


def requested_login(value):
    login(value)
    if not re.fullmatch(r"[a-z]+(?:-[a-z]+)*\.[a-z]+(?:-[a-z]+)*", value):
        raise ValueError("Le username doit respecter nom.prenom, en minuscules sans accents ni espaces (exemple : dupont.jean-pierre)")
    return value


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
            raise ValueError("Expected a list of at most ten keys per student")
        result[name] = []
        for value in keys:
            key = public_key(value)
            if key in seen:
                raise ValueError("Duplicate key within or across student accounts")
            seen.add(key)
            result[name].append(key)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("keys")
    args = parser.parse_args()
    load_keys(args.keys)
    print("Student access data is valid")
