# Student access automation

The public GitHub form creates an issue without prior student registration.
A workflow validates the requested `nom.prenom` username and opens a pull request changing only
`ansible/group_vars/student_ssh_keys.yml`. The teacher reviews and merges it.
A timer on the gateway (the current Ansible controller) reads that file from the configured branch and applies
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
submissions. Each account can have up to ten distinct keys. Requests only add
keys and deduplicate them; they never replace existing keys. The teacher must
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
requests can be corrected and then closed/reopened. Once a branch has been
created, the proposal is immutable: open a new issue for corrections and close
the superseded PR. If PR creation fails after branch creation, recover by
opening a PR from `student-access/issue-N`, or delete that branch after checking
it has no active PR and reopen the issue. Concurrent proposals touching the
same keys file may conflict; resolve them before merging and rerun validation.

## 3. Enable automatic synchronization on the gateway

First update the controller copy with this version of the project, including
`access/` and the updated `ansible/roles/students/` role. Use the gateway checkout
from which you already run Ansible. Preserve the controller's inventory
and its existing keys file when updating. Synchronization merges approved Git
keys with the current controller file and previously applied keys. Ansible adds
them with `exclusive: false`, retaining keys already present on the server too.
If the previous version was installed, update both the local student role and
rerun the synchronizer installer to switch off the old replacement behavior.

On the gateway, as the existing Ansible user (normally `ubuntu`), install once:

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
in a mode-0600 file on the gateway, and set `token_file` to its absolute path.
For a public repository no read token is needed. The gateway must reach
`api.github.com` over HTTPS. Do not reuse the PR write token on the gateway.

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

Run only one timer, on the gateway. If an earlier installation enabled one on
the bastion, disable it there with `systemctl --user disable --now student-access.timer`
and let any active service run finish before enabling the gateway timer.

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
it retains previously applied keys even when they are later removed from Git.
There is no permanent GitHub Actions runner on the gateway.

## Student procedure

The full exercise is in [TP 01](../../../tp/01-big-data-hadoop/README.md).

1. Generate a local Ed25519 key using the [connection guide](../docs/student-connection.md).
2. Open Issues → New issue → **Accès SSH au cluster** using any GitHub account.
3. Enter your username in `nom.prenom` format, for example `dupont.alice`.
4. Paste the `.pub` content, one key per line. Never submit the private key.
5. Wait for teacher review and gateway synchronization, then connect with that username.

Requests, usernames and public keys are visible to anyone who can read the
repository. Do not submit personal email addresses or other unnecessary data.

## Preservation and manual revocation

Removing a key or account from Git, setting a key list to `[]`, or reverting a
commit does **not** revoke any existing SSH access. The workflow and synchronizer
only add keys. Existing accounts and HDFS data remain. The role refuses reserved
names and existing accounts whose primary group is not the student group.

Revocation is a separate administrator operation: pause the timer, remove the
key from Git, the controller keys file, the applied state file
`~/.local/share/student-access/state/applied.yml`, and the student's
`authorized_keys` on the gateway before restarting the timer. Otherwise a retained
copy could add the key again. Existing sessions and jobs are unaffected.
To pause:

```bash
systemctl --user disable --now student-access.timer
# If a run is already active, wait for it or explicitly stop the service.
```

Local playbooks and synchronizer code are updated manually using the installer;
merging changes to those files does not deploy executable code to the gateway.

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
