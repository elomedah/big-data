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

from validate import load_keys, public_key, requested_login, school, school_keys_path

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
    keys = list(dict.fromkeys(keys))
    if not keys or len(keys) > 10:
        raise ValueError("Fournir entre une et dix clés distinctes")
    return name, keys


def apply_request(mapping, name, keys):
    requested_login(name)
    updated = {user: list(values) for user, values in mapping.items()}
    updated[name] = list(dict.fromkeys(keys))
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
        school_sections = re.findall(r"^### École\s*\n([^#]+)", issue["body"].replace("\r\n", "\n"), flags=re.MULTILINE)
        if len(school_sections) != 1:
            raise ValueError("Saisissez votre école dans le formulaire")
        selected_school = school(school_sections[0].strip())
        keys_file = school_keys_path(selected_school)
        base = api("GET", "")["default_branch"]
        sha = api("GET", "/git/ref/heads/" + quote(base, safe=""))["object"]["sha"]

        def content(path):
            return api("GET", "/contents/" + path + "?ref=" + sha)

        source = content(keys_file)
        with tempfile.TemporaryDirectory() as directory:
            keys_path = Path(directory) / "keys.yml"
            keys_path.write_bytes(base64.b64decode(source["content"]))
            mapping = load_keys(keys_path)
            updated = apply_request(mapping, name, keys)
            if updated == mapping:
                api("POST", f"/issues/{number}/comments", {"body": "Ces clés sont déjà enregistrées dans le dépôt."})
                api("PATCH", f"/issues/{number}", {"state": "closed", "state_reason": "completed"})
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
        api("PUT", "/contents/" + keys_file, {"message": f"Update {selected_school} student access from issue #{number}",
            "branch": branch, "sha": source["sha"], "content": base64.b64encode(serialized.encode()).decode()})
        pr = api("POST", "/pulls", {"title": f"Accès étudiant {selected_school} : demande #{number}", "head": branch,
            "base": base, "body": f"Remplace les clés du compte `{name}`, demandé par @{issue['user']['login']}. Seules les clés de cette demande seront conservées.\n\n"
            f"Vérifier que le demandeur est bien autorisé à utiliser ce compte, surtout s'il existe déjà. La synchronisation depuis le bastion intervient après fusion.\n\nCloses #{number}"})
        api("POST", f"/issues/{number}/comments", {"body": "Proposition prête à vérifier : " + pr["html_url"]})
    except ValueError as exc:
        reasons = {
            "Expected one public key per line": "Chaque clé publique SSH doit être fournie sur une seule ligne.",
            "Only plain ssh-ed25519 public keys are accepted": "Seules les clés publiques SSH au format ssh-ed25519 sont acceptées. Fournissez le contenu du fichier .pub, jamais une clé privée.",
            "Invalid public key encoding": "L'encodage de la clé publique SSH est invalide. Copiez la ligne complète du fichier .pub.",
            "Invalid Ed25519 public key structure": "La clé publique Ed25519 est incomplète ou invalide. Copiez la ligne complète du fichier .pub.",
            "Invalid or reserved student login": "Le username doit respecter nom.prenom, en minuscules sans accents ni espaces, avec au maximum 32 caractères.",
            "Duplicate key within or across student accounts": "Cette clé publique SSH est déjà associée à un autre compte étudiant.",
        }
        reason = reasons.get(str(exc), str(exc))
        api("POST", f"/issues/{number}/comments", {"body":
            "**Demande refusée — clé SSH non acceptée.**\n\n"
            f"Motif : {reason}\n\n"
            "Aucun accès n'a été accordé par cette demande. Cette issue est clôturée automatiquement. "
            "Corrigez les informations indiquées puis soumettez une nouvelle demande via le formulaire Accès SSH au cluster."})
        api("PATCH", f"/issues/{number}", {"state": "closed", "state_reason": "not_planned"})


if __name__ == "__main__":
    main()
