# Student access automation

## Listes par école

Le formulaire demande de saisir librement le nom de l'école, sans afficher
les autres établissements. Les erreurs de validation ne citent pas les écoles
acceptées. Les fichiers et les issues restent visibles aux lecteurs du dépôt.
Une expression régulière construite depuis la liste interne des écoles reconnaît
le nom dans le texte saisi, sans tenir compte des majuscules (par exemple un nom
suivi de la ville). Le nom doit être un mot complet ; une saisie mentionnant
plusieurs écoles différentes est refusée.
Chaque demande modifie uniquement le fichier de l'école sélectionnée :

- `ansible/group_vars/student_ssh_keys_ensitech.yml`
- `ansible/group_vars/student_ssh_keys_iris.yml`
- `ansible/group_vars/student_ssh_keys_efrei.yml`

Ces trois fichiers utilisent le format `student_ssh_keys: {nom.prenom: [clé publique]}`.
Ils sont initialement vides. La liste historique `student_ssh_keys.yml` reste
conservée : déplacer manuellement chaque entrée vers son école quand elle est
connue, en retirant l'entrée du fichier historique dans le même changement.
Chaque installation sélectionne une seule école. Les fichiers sont validés
indépendamment. Les clés identiques sur des comptes différents d'une même école
sont refusées.

Ansible charge uniquement la liste choisie par le paramètre obligatoire
`student_school` (`ensitech`, `iris` ou `efrei`) :

```bash
cd infra-hadoop/scaleway/ansible
ansible-playbook -i inventory.ini site.yml --tags students -e student_school=iris
```

Pour une installation complète, retirer `--tags students` et conserver `-e`.
Le paramètre peut aussi être défini dans l'inventaire du cluster. Les autres
listes et le fichier historique ne sont pas chargés. Une liste vide est acceptée.
Changer d'école ne supprime pas les comptes ni les accès déjà installés.

Le synchroniseur récupère uniquement le fichier de l'école configurée et
conserve un état distinct par école dans `state/<école>/`.
Pour activer cette évolution sur le bastion, mettre à jour les fichiers locaux
(y compris les trois fichiers d'école et le rôle students), puis relancer
`bash access/install-sync.sh "$PWD/ansible" elomedah/big-data main iris`.
Les changements de code locaux ne sont pas déployés par une fusion GitHub.

The public GitHub form creates an issue without prior student registration.
A workflow validates the requested `nom.prenom` username and opens a pull request changing only
the selected school's `ansible/group_vars/student_ssh_keys_<school>.yml`. The teacher reviews and merges it.
A timer on the bastion (the Ansible controller) reads that file from the configured branch and applies
the **locally installed** Ansible student role. No remote playbook or workflow
is fetched from Git, and no cluster SSH private key is stored in GitHub.

## 1. Public form and username

On a public repository, any signed-in GitHub user can submit the form; there
is no registry or allowlist. GitHub Issues requires a GitHub account, so this
is not an anonymous form. Open:

https://github.com/elomedah/big-data/issues/new?template=student-access.yml

The required username is **surname.firstname**, for example `dupont.alice`
or `le-gall.jean-pierre`. Use lowercase ASCII letters, exactly one dot, no
accents or spaces, and at most 32 characters. Hyphens may separate components
of either name. Validation is performed by the workflow after submission.
Existing legacy accounts such as `student01` remain valid in the keys file.

Only plain Ed25519 public keys are accepted; comments are removed from form
submissions. Each account can have up to ten distinct keys. Duplicate submitted
keys are accepted and stored once. Each request replaces that account's key list;
include every key that should retain access. The teacher must
verify the requester is entitled to use the requested account before merging,
especially when that account already exists or two students share a name.

## 2. Configure GitHub

Push these files to the default branch and enable Issues and GitHub Actions.
Create a fine-grained personal access token restricted to this repository with
**Contents: read/write**, **Pull requests: read/write**, and **Issues: read/write**.
Store it as the Actions secret `STUDENT_PR_TOKEN`. Use an automation account
where available, set an expiry and arrange renewal. A GitHub App installation
token is an alternative if the workflow is adapted to generate one.

A separate token is used so the generated PR triggers its validation workflow;
PRs created with the default `GITHUB_TOKEN` do not normally trigger another
workflow. See [GitHub authentication documentation](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token).

Protect the default branch with:

- Pull requests required, force pushes blocked.
- Required code-owner review (`.github/CODEOWNERS` names `@elomedah`).
- Dismiss stale approvals when new commits arrive.
- Required check `validate` from `Student access validation`, with branches
  required to be up to date before merging.

If the token belongs to the teacher, the automated PR is authored by the teacher;
use a separate automation account if your rules require that teacher to approve
it. Availability of branch-protection features depends on the repository/plan.

The request workflow processes opened or reopened issues, not edits. Invalid
requests receive a clear refusal comment explaining the validation failure and
are automatically closed as not planned. Submit a new form after correcting the
reported problem. Technical failures (such as a GitHub API error) leave the issue
open so the workflow can be retried. Once a branch has been
created, the proposal is immutable: open a new issue for corrections and close
the superseded PR. If PR creation fails after branch creation, recover by
opening a PR from `student-access/issue-N`, or delete that branch after checking
it has no active PR and reopen the issue. Concurrent proposals touching the
same keys file may conflict; resolve them before merging and rerun validation.

## 3. Enable automatic synchronization on the bastion

First update the controller copy with this version of the project, including
`access/` and the updated `ansible/roles/students/` role. Use the bastion checkout
from which you already run Ansible. Preserve the controller's inventory
and its existing keys file when updating. For accounts present in Git,
synchronization replaces the controller key list with the approved list.
Accounts omitted from Git retain their last known list. Ansible writes each
managed account's complete `authorized_keys` file, removing unlisted keys.
If the previous version was installed, update both the local student role and
rerun the synchronizer installer to enable replacement behavior. The next
synchronization reapplies the approved lists even if the Git data is unchanged.

On the bastion, as the existing Ansible user (normally `ubuntu`), install once:

```bash
sudo apt-get install -y python3-venv
cd ~/infra-hadoop/scaleway
bash access/install-sync.sh "$PWD/ansible" elomedah/big-data main iris
```

Ansible must already be installed and able to reach the cluster using the
existing inventory and SSH key. Its Python interpreter must have PyYAML
(normally included with Ansible). The cluster and HDFS must be running.

Review `~/.local/share/student-access/config.json`. For a private repository,
create a separate read-only token with repository Contents read access, save it
in a mode-0600 file on the bastion, and set `token_file` to its absolute path.
For a public repository no read token is needed. The bastion must reach
`api.github.com` over HTTPS. Do not reuse the PR write token on the bastion.

The installer enables the timer immediately and uses `sudo loginctl enable-linger`
so it continues after logout and starts again after reboot. The first check runs
about five seconds after installation, then every two minutes after a run ends.
It records the absolute path to your Ansible executable, including virtualenvs.
Ansible's SSH credentials and privilege escalation must work without interactive
password prompts. No service restart or manual Ansible run is needed after a PR
is merged. Inspect the timer and deployment journal with:

```bash
journalctl --user -u student-access.service -n 50
systemctl --user list-timers student-access.timer
```

Run only one timer, on the bastion. Install the synchronizer and Ansible there.
The gateway receives student keys through Ansible; it needs no synchronization
timer or local Ansible controller installation.

The timer checks every two minutes after the previous run finishes.
It serializes runs, fetches the keys from a single commit, validates them,
and runs `ansible-playbook site.yml --tags students` only when needed. Failures
are recorded in the journal and retried. The success marker is written only
after Ansible succeeds. Ansible can partially apply before failing; a retry
converges the remaining tasks. A failed HDFS step may occur after SSH keys were
already installed. A merged PR means approved, not necessarily deployed;
the service journal is the deployment status.

The original controller keys are backed up to
`~/.local/share/student-access/state/initial-keys.yml`. Retain the state directory:
it retains accounts omitted from Git, but never restores superseded keys for
accounts with an explicit Git entry.
There is no permanent GitHub Actions runner on the bastion.

## Student procedure

The full exercise is in [TP 01](../../../tp/01-big-data-hadoop/README.md).

1. Generate a local Ed25519 key using the [connection guide](../docs/student-connection.md).
2. Open Issues → New issue → **Accès SSH au cluster** using any GitHub account.
3. Enter your username in `nom.prenom` format, for example `dupont.alice`.
4. Paste the `.pub` content, one key per line. Never submit the private key.
5. Wait for teacher review and synchronization from the bastion, then connect with that username.

Requests, usernames and public keys are visible to anyone who can read the
repository. Do not submit personal email addresses or other unnecessary data.

## Key replacement and revocation

Removing a key from an account's Git list revokes that key after successful
synchronization. Setting its list to `[]` clears all its authorized keys;
this requires a direct reviewed edit because the public form requires a key.
Removing the entire account entry preserves its last known keys instead.
Reverting a commit restores the key lists in that commit. Existing accounts
and HDFS data remain. The role refuses reserved
names and existing accounts whose primary group is not the student group.

For revocation, keep the account entry in Git and submit the complete remaining
key list (or `[]`) for review. Existing sessions and jobs are unaffected.
For an urgent manual intervention, pause the timer and update both Git and the
gateway's `authorized_keys` before restarting synchronization. To pause:

```bash
systemctl --user disable --now student-access.timer
# If a run is already active, wait for it or explicitly stop the service.
```

Local playbooks and synchronizer code are updated manually using the installer;
merging changes to those files does not deploy executable code to the bastion.

## Tests

```bash
python3 -m pip install -r infra-hadoop/scaleway/access/requirements.txt
python3 -m unittest discover -s infra-hadoop/scaleway/access -p 'test_*.py' -v
python3 infra-hadoop/scaleway/access/validate.py \
  infra-hadoop/scaleway/ansible/group_vars/student_ssh_keys.yml
```

Linux is required for the synchronization test (`fcntl.flock`). The remaining
validation and request tests also run on Windows. No test contacts GitHub or
changes a live cluster.
