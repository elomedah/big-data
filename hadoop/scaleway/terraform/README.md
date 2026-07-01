# Terraform Scaleway Hadoop Cluster

This Terraform project creates the Scaleway infrastructure described in
`../../scaleway-cluster.md`:

- 1 public bastion for administration.
- 1 public student gateway.
- 1 private Hadoop master.
- 3 private Hadoop workers.
- A private network.
- Security groups.
- Block volumes for Hadoop metadata and HDFS data.

## Where to run Terraform and Ansible

Install Terraform and Ansible either on your local machine or on an
administration host.

Recommended setup on Windows:

```text
Windows + WSL Ubuntu
```

Install and run these tools inside WSL:

```text
terraform
ansible
ssh client
```

Terraform creates the Scaleway infrastructure. Ansible then connects to the
servers over SSH and installs Hadoop.

Alternative setup:

```text
Local computer: Terraform
Bastion server: Ansible
```

In that case, run Terraform locally first, then copy this project and your SSH
key to the bastion, install Ansible there, and run the playbook from the
bastion.

## Generate an SSH key

Generate a dedicated SSH key for this cluster:

```bash
chmod +x generate-ssh-key.sh
./generate-ssh-key.sh
```

By default, this creates:

```text
~/.ssh/m2-hadoop-scaleway
~/.ssh/m2-hadoop-scaleway.pub
```

Terraform reads the generated public key directly from this path:

```hcl
admin_ssh_public_key_path = "~/.ssh/m2-hadoop-scaleway.pub"
```

To choose another path or comment:

```bash
./generate-ssh-key.sh ~/.ssh/my-scaleway-key teacher@example
```

Then set the matching public key path:

```hcl
admin_ssh_public_key_path = "~/.ssh/my-scaleway-key.pub"
```

## Usage

```bash
export SCW_ACCESS_KEY="..."
export SCW_SECRET_KEY="..."
export SCW_DEFAULT_PROJECT_ID="..."

cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
terraform output -raw ansible_inventory > ../ansible/inventory.ini
```

Then run Ansible from `../ansible`.

## Sizing profiles

The `cluster_size` variable selects the machine sizing:

- `tiny`: test profile, uses very small `DEV1-S` instances and limits every
  data volume to 20 GB.
- `large`: teaching profile, keeps the original proportions from
  `../../scaleway-cluster.md`.

Example:

```hcl
cluster_size = "tiny"
```

For the full teaching cluster:

```hcl
cluster_size = "large"
```

## Notes

- `teacher_ssh_cidr = "0.0.0.0/0"` and `student_ssh_cidrs = ["0.0.0.0/0"]`
  allow SSH from every IPv4 address. This is convenient for temporary tests,
  but restrict these values before using the cluster with students.
- Internal nodes are reachable through the bastion with SSH `ProxyJump`.
- Data disks are attached to the master and workers. The Ansible storage role
  defaults to `/dev/vdb`; override `hadoop_data_device` if Scaleway exposes a
  different device path.
