# Terraform Scaleway Hadoop Cluster

This Terraform project creates the Scaleway infrastructure described in
`../../scaleway-cluster.md`:

- 1 public bastion for administration.
- 1 public student gateway.
- 1 private Hadoop master.
- Private Hadoop workers. The default is 3 workers in the `tiny` profile and
  5 workers in the `large` teaching profile.
- A private network.
- Reserved private IPs through Scaleway IPAM.
- Optional public IPs on private nodes for outbound internet during
  provisioning.
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

Install Terraform on Ubuntu/WSL:

```bash
sudo apt-get update
sudo apt-get install -y wget gpg lsb-release software-properties-common
wget -O - https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(grep -oP '(?<=UBUNTU_CODENAME=).*' /etc/os-release || lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt-get update
sudo apt-get install -y terraform
```

Install Ansible on Ubuntu/WSL:

```bash
sudo apt-get update
sudo apt-get install -y software-properties-common
sudo add-apt-repository --yes --update ppa:ansible/ansible
sudo apt-get install -y ansible
```

Check the installation:

```bash
terraform version
ansible --version
ssh -V
```

Terraform `>= 1.10.0` is required because the Scaleway Object Storage backend
uses native S3 lock files with `use_lockfile = true`.

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

## Remote Terraform state

This project stores Terraform state in Scaleway Object Storage through the
Terraform `s3` backend. Native S3 lock files are enabled with
`use_lockfile = true`, so concurrent `terraform apply` runs do not corrupt the
state.

The backend is defined in:

```text
backend.tf
```

The bucket name is intentionally not committed because Object Storage bucket
names must be globally unique. Create a local backend config from the example:

```bash
cp backend.hcl.example backend.hcl
```

Edit `backend.hcl`:

```hcl
bucket = "m2-hadoop-terraform-state-your-unique-suffix"
```

Create the bucket in Scaleway Object Storage before running `terraform init`.
You can do it from the Scaleway console, or with an S3-compatible CLI.

Install AWS CLI on Ubuntu/WSL:

```bash
sudo apt-get update
sudo apt-get install -y unzip curl

curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" \
  -o "awscliv2.zip"

unzip awscliv2.zip
sudo ./aws/install

aws --version
```

Then configure AWS-compatible environment variables for Scaleway Object
Storage. This step is required by Terraform's `s3` backend; it does not read
`SCW_ACCESS_KEY` and `SCW_SECRET_KEY` directly.

```bash
export AWS_ACCESS_KEY_ID="$SCW_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="$SCW_SECRET_KEY"
export AWS_DEFAULT_REGION="fr-par"
```

If Terraform reports `No valid credential sources found`, check that the AWS
variables are present in the same shell where you run `terraform init`:

```bash
env | grep '^AWS_'
```

Create the bucket:

```bash
aws --endpoint-url https://s3.fr-par.scw.cloud \
  s3api create-bucket \
  --bucket m2-hadoop-terraform-state-your-unique-suffix \
  --region fr-par
```

Enable bucket versioning so an older state can be recovered after a bad write
or accidental deletion:

```bash
aws --endpoint-url https://s3.fr-par.scw.cloud \
  s3api put-bucket-versioning \
  --bucket m2-hadoop-terraform-state-your-unique-suffix \
  --versioning-configuration Status=Enabled
```

Initialize Terraform with the remote backend:

```bash
terraform init -backend-config=backend.hcl
```

If the backend configuration was already initialized before this repository
used `endpoints.s3`, reconfigure it:

```bash
terraform init -backend-config=backend.hcl -reconfigure
```

If you already have a local `terraform.tfstate`, migrate it to Scaleway Object
Storage:

```bash
terraform init -backend-config=backend.hcl -migrate-state
```

After migration, run:

```bash
terraform plan
```

Review the plan carefully. Terraform should not try to recreate the existing
cluster just because the state was moved.

Do not commit these local files:

```text
terraform.tfstate
terraform.tfstate.backup
terraform.tfvars
backend.hcl
.terraform/
```

## Usage

```bash
export SCW_ACCESS_KEY="..."
export SCW_SECRET_KEY="..."
export SCW_DEFAULT_PROJECT_ID="..."
export AWS_ACCESS_KEY_ID="$SCW_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="$SCW_SECRET_KEY"
export AWS_DEFAULT_REGION="fr-par"

cp terraform.tfvars.example terraform.tfvars
cp backend.hcl.example backend.hcl
terraform init -backend-config=backend.hcl
terraform plan
terraform apply
terraform output -raw ansible_inventory > ../ansible/inventory.ini
```

Get the bastion public IP:

```bash
terraform output -raw bastion_public_ip
```

Prepare the bastion for Ansible. This copies the whole `infra-hadoop/scaleway`
project, installs the bastion inventory, and copies the private SSH key needed
to reach private nodes:

```bash
chmod +x prepare-bastion.sh
./prepare-bastion.sh
```

By default, the script copies the project to:

```text
ubuntu@<bastion_public_ip>:infra-hadoop/scaleway
```

It excludes local Terraform state and secrets:

```text
terraform/.terraform
terraform/terraform.tfstate
terraform/terraform.tfstate.backup
terraform/terraform.tfvars
terraform/backend.hcl
```

It also installs the bastion inventory as:

```text
infra-hadoop/scaleway/ansible/inventory.ini
```

To use another private key or remote project directory:

```bash
./prepare-bastion.sh ~/.ssh/my-scaleway-key infra-hadoop/scaleway
```

Then run Ansible from `../ansible`, either from your local machine through the
bastion or after logging in to the bastion.

Connect to the bastion with the generated SSH key:

```bash
chmod +x connect-bastion.sh
./connect-bastion.sh
```

To use another private key:

```bash
./connect-bastion.sh ~/.ssh/my-scaleway-key
```


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

The number of workers is configurable per profile:

```hcl
tiny_worker_count  = 3
large_worker_count = 5
```

## Worker active and reduced modes

The `worker_mode` variable changes only the compute profile used by Hadoop
workers. It is intended for the pedagogical cost model where workers run with
full resources during TP sessions, about 25% of the time, and smaller resources
outside TP sessions, about 75% of the time.

The same `worker_mode` workflow applies to both `tiny` and `large`. This makes
it possible to test the resize procedure cheaply with `cluster_size = "tiny"`
before applying it to the full teaching cluster.

```hcl
cluster_size = "large"
worker_mode  = "active"
```

Outside TP sessions:

```hcl
cluster_size = "large"
worker_mode  = "reduced"
```

You can also pass these values directly on the command line.

Low-cost tiny test:

```bash
terraform apply \
  -var='cluster_size=tiny' \
  -var='worker_mode=active' \
  -var='worker_active_commercial_type=DEV1-S' \
  -var='worker_reduced_commercial_type=DEV1-S'
```

Large active mode for TP sessions:

```bash
terraform apply \
  -var='cluster_size=large' \
  -var='worker_mode=active' \
  -var='worker_active_commercial_type=DEV1-XL' \
  -var='worker_reduced_commercial_type=DEV1-L'
```

Large reduced mode outside TP sessions:

```bash
terraform apply \
  -var='cluster_size=large' \
  -var='worker_mode=reduced' \
  -var='worker_active_commercial_type=DEV1-XL' \
  -var='worker_reduced_commercial_type=DEV1-L'
```

The default instance type variables are:

```hcl
worker_active_commercial_type  = "DEV1-S"
worker_reduced_commercial_type = "DEV1-S"
```

These conservative defaults keep `tiny` cheap. For the `large` teaching
cluster, override the same variables with the exact Scaleway offers validated
in the quote, for example:

```hcl
worker_active_commercial_type  = "DEV1-XL"
worker_reduced_commercial_type = "DEV1-L"
```

The HDFS data volumes are separate `scaleway_block_volume` resources, so
changing `worker_mode` does not change their declared size.

For the full CPU/RAM resize procedure, including when to stop services and when
to rerun Ansible, see:

```text
../docs/cpu-ram-resizing.md
```

## Worker HDFS disk size

For the `large` profile, the HDFS data disk size attached to each worker is
configurable:

```hcl
large_worker_data_size_gb = 100
```

With the default 5 large workers, this gives:

```text
5 x 100 GB = 500 GB raw HDFS capacity
```

You can increase this value later to grow the attached Block Storage volumes.
Do not decrease it for an existing cluster: shrinking a filesystem/HDFS data
volume is not a safe operation and can lead to data loss.

Example: increase workers from 100 GB to 200 GB each.

```hcl
cluster_size = "large"
large_worker_data_size_gb = 200
```

Before running `terraform plan` or `terraform apply` for a VM resize, stop the
cluster services with Ansible:

```bash
cd infra-hadoop/scaleway/ansible
ansible-playbook stop-services.yml
```

Apply the Terraform change:

```bash
terraform plan
terraform apply
```

After Scaleway has increased the Block Storage volumes, rerun the Ansible
storage role. It is configured to resize the existing ext4 filesystem
idempotently.

```bash
cd infra-hadoop/scaleway/ansible
ansible-playbook site.yml --tags storage
```

```bash
cd infra-hadoop/scaleway/ansible
ansible-playbook start-services.yml
```

Then verify HDFS and rebalance if needed:

```bash
hdfs dfsadmin -report
hdfs balancer
```

Recommended workflow:

```bash
# Stop cluster services before any worker compute resize
cd ../ansible
ansible-playbook stop-services.yml

# Before TP, switch workers to active size
cd ../terraform
terraform apply \
  -var='cluster_size=large' \
  -var='worker_mode=active' \
  -var='worker_active_commercial_type=DEV1-XL' \
  -var='worker_reduced_commercial_type=DEV1-L'

# After TP, switch workers to reduced size
terraform apply \
  -var='cluster_size=large' \
  -var='worker_mode=reduced' \
  -var='worker_active_commercial_type=DEV1-XL' \
  -var='worker_reduced_commercial_type=DEV1-L'

# Reconfigure and restart services after the resize
cd ../ansible
ansible-playbook site.yml
# Or, if the machines were only resized and are already configured:
ansible-playbook start-services.yml
```

`stop-services.yml` stops Hive, HBase, Spark history, YARN and HDFS services in
a clean order before Terraform resizes the workers.

## Final teardown

At the end of the module, Terraform can destroy the full infrastructure,
including VMs, public IPs, private network resources, security groups and Block
Storage data volumes.

This permanently deletes HDFS data.

Data volumes are protected by default with `prevent_destroy = true` in
`main.tf`. Terraform does not allow `prevent_destroy` to be controlled by a
variable, so final deletion requires an explicit code change.

Before destroying the infrastructure, stop the Hadoop services cleanly if the
cluster is still running:

```bash
cd ../ansible
ansible-playbook shutdown.yml
```

Then remove the protection block from `scaleway_block_volume.data` in `main.tf`:

```hcl
lifecycle {
  prevent_destroy = true
}
```

Finally, destroy the Scaleway infrastructure from the Terraform directory:

```bash
cd ../terraform
terraform plan -destroy
terraform destroy
```

After the command completes, verify in the Scaleway console that no unexpected
instances, Block Storage volumes, snapshots or public IPs remain.

## Notes

- `teacher_ssh_cidr = "0.0.0.0/0"` and `student_ssh_cidrs = ["0.0.0.0/0"]`
  allow SSH from every IPv4 address. This is convenient for temporary tests,
  but restrict these values before using the cluster with students.
- Internal nodes are reachable through the bastion with SSH `ProxyJump`.
- Private node addresses are reserved from `private_subnet`, which defaults to
  `10.42.0.0/24`.
- `allocate_public_ip_to_private_nodes = true` gives master and workers
  outbound internet access for `apt` and Hadoop downloads. Their security group
  still blocks public inbound access.
- `student_web_cidrs` controls who can access web UIs through the gateway
  public IP. It defaults to `["0.0.0.0/0"]` for tests. Terraform opens the
  Nginx reverse-proxy ports for NameNode `9870`, YARN ResourceManager `8088`,
  MapReduce HistoryServer `19888`, HBase Master `16010`, and per-worker
  DataNode, NodeManager and HBase RegionServer ports derived from the
  configured worker count. It also opens Spark History Server `18080` and
  HiveServer2 Web UI `10002`, which are served directly by services running on
  the gateway and are not handled by Nginx. Spark application UIs on
  `4040-4050` are not proxied because those ports are ephemeral and may be
  owned directly by Spark drivers on the gateway.
- Data disks are attached to the master and workers as separate Block Storage
  volumes. They survive worker compute resizing and are protected by default
  with `prevent_destroy = true`. Terraform lifecycle settings cannot be driven
  by variables, so intentional final deletion requires removing that lifecycle
  block before running `terraform destroy`.
- The Ansible storage role defaults to `/dev/vdb`; override
  `hadoop_data_device` if Scaleway exposes a different device path.
