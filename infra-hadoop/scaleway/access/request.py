"""Process a GitHub issue as data; never interpolate its content into a shell."""
import base64
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

import yaml

from validate import load_keys, public_key, requested_login

KEYS = "infra-hadoop/scaleway/ansible/group_vars/student_ssh_keys.yml"


def parse_request(body):
    if not isinstance(body, str) or len(body) > 16000:
        raise ValueError("Demande vide ou trop longue")
    sections = re.split(r"^### ", body.replace("\r\n", "\n"), flags=re.MULTILINE)
    fields = {}
    for section in sections[1:]:
        heading, _, value = section.partition("\n")
        if heading in fields:
            raise ValueError("Champ dupliqué")
        fields[heading] = value.strip()
    name = requested_login(fields.get("Username (nom.prenom)", ""))
    value = fields.get("Clés publiques SSH", "")
    if value.startswith("```text\n") and value.endswith("\n```"):
        value = value[len("```text\n"):-len("\n```")]
    keys = [public_key(line.strip()) for line in value.splitlines() if line.strip()]
    if not keys or len(keys) > 10 or len(keys) != len(set(keys)):
        raise ValueError("Fournir entre une et dix clés distinctes")
    return name, keys


def apply_request(mapping, name, keys):
    requested_login(name)
    updated = {user: list(values) for user, values in mapping.items()}
    current = updated.get(name, [])
    updated[name] = list(dict.fromkeys(current + keys))
    return updated


def main():
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise ValueError("Configurer le secret STUDENT_PR_TOKEN (voir access/README.md)")
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    repo = os.environ["GITHUB_REPOSITORY"]
    number = event["issue"]["number"]

    def api(method, path, data=None):
        request = Request("https://api.github.com/repos/" + repo + path,
                          data=json.dumps(data).encode() if data is not None else None,
                          method=method, headers={"Authorization": "Bearer " + token,
                          "Accept": "application/vnd.github+json", "User-Agent": "student-access",
                          "Content-Type": "application/json"})
        with urlopen(request, timeout=30) as response:
            return json.load(response)

    try:
        # Reload current issue: the event may have waited in a concurrency queue.
        issue = api("GET", f"/issues/{number}")
        if issue["state"] != "open" or "pull_request" in issue:
            return
        name, keys = parse_request(issue["body"])
        base = api("GET", "")["default_branch"]
        sha = api("GET", "/git/ref/heads/" + quote(base, safe=""))["object"]["sha"]

        def content(path):
            return api("GET", "/contents/" + path + "?ref=" + sha)

        source = content(KEYS)
        with tempfile.TemporaryDirectory() as directory:
            keys_path = Path(directory) / "keys.yml"
            keys_path.write_bytes(base64.b64decode(source["content"]))
            mapping = load_keys(keys_path)
            updated = apply_request(mapping, name, keys)
            if updated == mapping:
                api("POST", f"/issues/{number}/comments", {"body": "Ces clés sont déjà enregistrées dans le dépôt."})
                return
            serialized = yaml.safe_dump({"student_ssh_keys": updated}, sort_keys=True)
            keys_path.write_text(serialized, encoding="utf-8")
            load_keys(keys_path)
        # One immutable proposal per issue. Edits never overwrite a reviewed PR.
        branch = f"student-access/issue-{number}"
        try:
            api("GET", "/git/ref/heads/" + branch)
        except HTTPError as exc:
            if exc.code != 404:
                raise
        else:
            api("POST", f"/issues/{number}/comments", {"body":
                "Une proposition existe déjà pour cette demande. Pour une correction, ouvrir une nouvelle demande ; ne pas réutiliser cette issue."})
            return
        api("POST", "/git/refs", {"ref": "refs/heads/" + branch, "sha": sha})
        api("PUT", "/contents/" + KEYS, {"message": f"Update student access from issue #{number}",
            "branch": branch, "sha": source["sha"], "content": base64.b64encode(serialized.encode()).decode()})
        pr = api("POST", "/pulls", {"title": f"Accès étudiant : demande #{number}", "head": branch,
            "base": base, "body": f"Ajoute des clés au compte `{name}`, demandé par @{issue['user']['login']}. Les clés existantes sont conservées.\n\n"
            f"Vérifier que le demandeur est bien autorisé à utiliser ce compte, surtout s'il existe déjà. La synchronisation depuis le bastion intervient après fusion.\n\nCloses #{number}"})
        api("POST", f"/issues/{number}/comments", {"body": "Proposition prête à vérifier : " + pr["html_url"]})
    except ValueError as exc:
        api("POST", f"/issues/{number}/comments", {"body": "Demande refusée : " + str(exc) + ". Corriger puis fermer et rouvrir cette issue."})
        raise


if __name__ == "__main__":
    main()
