# Ansible Hadoop Installation

This Ansible project configures the Scaleway servers created by
`../terraform`.

It installs and configures:

- Java and base Linux packages.
- A `hadoop` system user.
- Linux resource limits for students.
- Mounted data disks on the master and workers.
- Hadoop HDFS, YARN and MapReduce.
- NameNode, DataNode, ResourceManager, NodeManager and History Server services.
- Student Linux accounts on the gateway.
- Student HDFS home directories and quotas.

## Prerequisites

Terraform must be applied first from `../terraform`.

From `hadoop/scaleway/terraform`:

```bash
terraform apply
```

Install required Ansible collections:

```bash
cd hadoop/scaleway/ansible
ansible-galaxy collection install -r requirements.yml
```

The SSH key used by Ansible must match the Terraform variable:

```hcl
admin_ssh_public_key_path = "~/.ssh/m2-hadoop-scaleway.pub"
```

## Option 1: Run Ansible Locally

Use this when Ansible is installed on your local machine or WSL.

Generate the local inventory:

```bash
cd hadoop/scaleway/terraform
terraform output -raw ansible_inventory > ../ansible/inventory.ini
```

Run the playbook:

```bash
cd ../ansible
ansible-playbook site.yml
```

This inventory uses SSH `ProxyJump` through the bastion to reach private nodes.

## Option 2: Run Ansible From The Bastion

Use this when Ansible is installed directly on the bastion.

From your local machine, copy the bastion-ready inventory:

```bash
cd hadoop/scaleway/terraform
chmod +x copy-inventory-to-bastion.sh
./copy-inventory-to-bastion.sh
```

Copy the private SSH key to the bastion:

```bash
chmod +x copy-private-key-to-bastion.sh
./copy-private-key-to-bastion.sh
```

Connect to the bastion:

```bash
chmod +x connect-bastion.sh
./connect-bastion.sh
```

On the bastion, install Ansible if needed:

```bash
sudo apt-get update
sudo apt-get install -y software-properties-common
sudo add-apt-repository --yes --update ppa:ansible/ansible
sudo apt-get install -y ansible
```

Then run:

```bash
cd hadoop/scaleway/ansible
ansible-galaxy collection install -r requirements.yml
ansible-playbook site.yml
```

## SSH Validation

Before running the full playbook from the bastion, test direct SSH to a private
node:

```bash
ssh -i /home/ubuntu/.ssh/m2-hadoop-scaleway ubuntu@10.42.0.12
```

Then test Ansible:

```bash
ansible hadoop -m ping
```

If this works, Ansible can reach the gateway, master and workers.

## Student SSH Keys

The playbook creates locked Linux accounts named:

```text
student01
student02
...
student30
```

Students should generate their own SSH key locally and send only the public key.

Student command:

```bash
ssh-keygen -t ed25519 -a 100 -f ~/.ssh/m2-hadoop-student -C student01
cat ~/.ssh/m2-hadoop-student.pub
```

The student sends the output of the `cat` command to the teacher. They must
never send the private key file.

Teacher workflow:

```bash
cp group_vars/student_ssh_keys.yml.example group_vars/student_ssh_keys.yml
```

Edit `group_vars/student_ssh_keys.yml`:

```yaml
student_ssh_keys:
  student01:
    - "ssh-ed25519 AAAA... student01@example"
  student02:
    - "ssh-ed25519 AAAA... student02@example"
```

Then rerun only the student role:

```bash
ansible-playbook site.yml --tags students
```

Students connect to the gateway:

```bash
ssh -i ~/.ssh/m2-hadoop-student student01@<gateway_public_ip>
```

## Troubleshooting

`Permission denied (publickey)` means the private network is reachable, but the
SSH key is not accepted by the target machine.

On the bastion, check the private key:

```bash
ssh-keygen -y -f /home/ubuntu/.ssh/m2-hadoop-scaleway
```

The output must match the public key configured by Terraform:

```hcl
admin_ssh_public_key_path = "~/.ssh/m2-hadoop-scaleway.pub"
```

If the key path was changed after the servers were created, recreate the
servers so cloud-init injects the correct key.

APT errors on private nodes usually mean they cannot reach the internet.
Terraform defaults to:

```hcl
allocate_public_ip_to_private_nodes = true
```

This gives master and workers outbound internet access for `apt` and downloads,
while security groups still block public inbound access.

## Device Name

The storage role uses automatic disk detection by default:

```yaml
hadoop_data_device: auto
```

It excludes the root disk and uses the attached data disk for `/data/hadoop`.

If detection fails, connect to the failing host and inspect disks:

```bash
lsblk -f
```

Then override the value in `group_vars/all.yml`, for example:

```yaml
hadoop_data_device: /dev/sdb
```

Then rerun the playbook.
