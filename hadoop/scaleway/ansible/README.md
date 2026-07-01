# Ansible Hadoop Installation

This Ansible project configures the servers created by
`../terraform`:

- Java and base packages.
- A Hadoop user and Linux resource limits.
- Mounted data disks on the master and workers.
- Hadoop HDFS, YARN and MapReduce configuration.
- NameNode, DataNode, ResourceManager, NodeManager and History Server
  systemd services.
- Student Linux accounts on the gateway.
- Student HDFS home directories and quotas.

## Usage

From `hadoop/scaleway/terraform`:

```bash
terraform output -raw ansible_inventory > ../ansible/inventory.ini
```

From `hadoop/scaleway/ansible`:

```bash
ansible-galaxy collection install -r requirements.yml
ansible-playbook site.yml
```

## Run Ansible from the bastion

If you prefer to run Ansible from the bastion, connect to it first:

```bash
ssh -i ~/.ssh/m2-hadoop-scaleway ubuntu@<bastion_public_ip>
```

Or use the Terraform helper script:

```bash
cd hadoop/scaleway/terraform
./connect-bastion.sh
```

You can get the bastion IP from Terraform:

```bash
cd hadoop/scaleway/terraform
terraform output -raw bastion_public_ip
```

On the bastion, install Ansible:

```bash
sudo apt-get update
sudo apt-get install -y software-properties-common
sudo add-apt-repository --yes --update ppa:ansible/ansible
sudo apt-get install -y ansible
```

Copy the project directory and the private SSH key to the bastion before
running Ansible. The private key must match `admin_ssh_public_key_path` from
Terraform.

From your local Terraform directory, generate and copy the bastion-ready
inventory:

```bash
cd hadoop/scaleway/terraform
./copy-inventory-to-bastion.sh
```

This creates `../ansible/inventory-bastion.ini` locally and copies it to the
bastion as:

```text
~/hadoop/scaleway/ansible/inventory.ini
```

Then run:

```bash
cd hadoop/scaleway/ansible
ansible-galaxy collection install -r requirements.yml
ansible-playbook site.yml
```

## SSH access

The generated inventory connects to private nodes through the bastion with
`ProxyJump`. Use the private key matching `admin_ssh_public_key_path` from
Terraform.

## Student keys

The playbook creates locked Linux accounts named `student01` to `student30`.
Students should generate their own SSH key locally and send only the public
key.

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

Then rerun the student role:

```bash
ansible-playbook site.yml --tags students
```

Students connect to the gateway:

```bash
ssh -i ~/.ssh/m2-hadoop-student student01@<gateway_public_ip>
```

## Device name

The storage role uses `/dev/vdb` by default. If Scaleway exposes the attached
block volume under another path, change `hadoop_data_device` in
`group_vars/all.yml` and rerun the playbook.
