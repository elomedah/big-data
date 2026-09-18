# Student access automation

The GitHub form creates an issue. A workflow validates its author's GitHub
account against `roster.json` and opens a pull request changing only
`ansible/group_vars/student_ssh_keys.yml`. The teacher reviews and merges it.
A timer on the bastion reads that file from the configured branch and applies
the **locally installed** Ansible student role. No remote playbook or workflow
is executed on the bastion, and no cluster SSH private key is stored in GitHub.

## 1. Register identities

Edit `roster.json` on a teacher-reviewed branch, using real GitHub usernames:

```json
{
  "github_users": {
    "alice-github": "student01",
    "bob-github": "student02"
  }
}
```

The supplied registry is intentionally empty: existing student accounts and
keys are preserved, but no requester is authorized until registered. Never
approve a student changing this registry themselves. One GitHub account maps
to one Linux account. Existing manually managed students may remain outside
the registry. Only plain Ed25519 public keys are accepted; comments are removed
from form submissions. Each account can have up to ten distinct keys.

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
requests can be corrected and then closed/reopened. Once a branch has been
created, the proposal is immutable: open a new issue for corrections and close
the superseded PR. If PR creation fails after branch creation, recover by
opening a PR from `student-access/issue-N`, or delete that branch after checking
it has no active PR and reopen the issue. Concurrent proposals touching the
same keys file may conflict; resolve them before merging and rerun validation.

## 3. Install on the bastion

First update the controller copy with this version of the project, including
`access/` and the updated `ansible/roles/students/` role. You can use the existing
`terraform/prepare-bastion.sh` procedure. Preserve the controller's inventory
and review the keys file before copying: subsequent synchronization makes Git
authoritative for **all** keys of listed student accounts. Import any public
keys that must be retained into Git first.

On the bastion, as the existing Ansible user (normally `ubuntu`):

```bash
sudo apt-get install -y python3-venv
cd ~/infra-hadoop/scaleway
bash access/install-sync.sh "$PWD/ansible" elomedah/big-data main
```

Ansible must already be installed and able to reach the cluster using the
existing inventory and SSH key. Its Python interpreter must have PyYAML
(normally included with Ansible). The cluster and HDFS must be running.

Review `~/.local/share/student-access/config.json`. For a private repository,
create a separate read-only token with repository Contents read access, save it
in a mode-0600 file on the bastion, and set `token_file` to its absolute path.
The bastion must reach `api.github.com` over HTTPS. Do not reuse the PR write
token on the bastion.

Apply once, inspect the result, then enable periodic synchronization:

```bash
systemctl --user start student-access.service
journalctl --user -u student-access.service -n 50
sudo loginctl enable-linger "$(id -un)"
systemctl --user enable --now student-access.timer
systemctl --user list-timers student-access.timer
```

The installer deliberately does not start synchronization before this first
review. The timer checks every two minutes after the previous run finishes.
It serializes runs, fetches the keys from a single commit, validates them,
and runs `ansible-playbook site.yml --tags students` only when needed. Failures
are recorded in the journal and retried. The success marker is written only
after Ansible succeeds. Ansible can partially apply before failing; a retry
converges the remaining tasks. A failed HDFS step may occur after SSH keys were
already installed. A merged PR means approved, not necessarily deployed;
the service journal is the deployment status.

The original controller keys are backed up to
`~/.local/share/student-access/state/initial-keys.yml`. Retain the state directory:
it tracks accounts removed from Git so their SSH keys can be cleared.
There is no permanent GitHub Actions runner on the bastion.

## Student procedure

1. Generate a local Ed25519 key using the [connection guide](../docs/student-connection.md).
2. Open Issues → New issue → **Accès SSH au cluster** using the registered GitHub account.
3. Choose **Ajouter** to retain current keys, or **Remplacer** to replace all keys.
4. Paste the `.pub` content, one key per line. Never submit the private key.
5. Wait for teacher review and bastion synchronization, then connect with the assigned login.

Requests, usernames and public keys are visible to anyone who can read the
repository. Do not submit personal email addresses or other unnecessary data.

## Revocation and rollback

For explicit revocation, the teacher changes the student's entry to `[]` and
merges the PR. Removing an entry also revokes its keys on the next bastion
synchronization when the account is known in the local keys/state file.
Accounts and HDFS data remain. Revocation prevents new key-based SSH logins;
it does not terminate existing sessions or jobs. Remove the student's registry
entry too if they must no longer request new keys.

Direct Ansible execution clears keys only for listed students: retain an empty
entry when revoking without the timer. The role refuses reserved names and
existing accounts whose primary group is not the configured student group.
The entire `authorized_keys` file of each student is managed; manual extra keys
are removed on the next application. Teacher/admin keys are outside this scope.

To roll back, revert the relevant keys commit through a reviewed PR. The next
successful sync reapplies that version. To pause:

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
  infra-hadoop/scaleway/ansible/group_vars/student_ssh_keys.yml \
  --roster infra-hadoop/scaleway/access/roster.json
```

Linux is required for the synchronization test (`fcntl.flock`). The remaining
validation and request tests also run on Windows. No test contacts GitHub or
changes a live cluster.
