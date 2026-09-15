# CPU and RAM resizing with Terraform

This document explains how to resize the Scaleway instances used by the Hadoop
cluster.

Before running `terraform plan` or `terraform apply` for a VM resize, stop the
cluster services with Ansible:

```bash
cd infra-hadoop/scaleway/ansible
ansible-playbook stop-services.yml
```

This is required because Terraform may stop, resize or replace worker, gateway
or master VMs. Stopping services first avoids abrupt HDFS/YARN failures while
NameNode, DataNodes, ResourceManager, NodeManagers, Hive, Spark or HBase are
still running.

In Terraform, CPU and RAM are not configured directly as numeric values. They
are controlled by the Scaleway instance type, called `commercial_type`.

Default low-cost example:

```hcl
worker_active_commercial_type  = "DEV1-S"
worker_reduced_commercial_type = "DEV1-S"
```

Recommended teaching example when a worker must provide 16 vCPU during TP:

```hcl
worker_active_commercial_type  = "BASIC3-X16C-32G"
worker_reduced_commercial_type = "DEV1-L"
```

Check the Scaleway quote or console for the exact CPU/RAM attached to each
instance type before changing these values.

## DEV1 quick reference

The tiny and reduced examples use the DEV1 family to keep costs low:

| Type | vCPU | RAM |
| --- | ---: | ---: |
| `DEV1-S` | 2 vCPU | 2 GiB |
| `DEV1-M` | 3 vCPU | 4 GiB |
| `DEV1-L` | 4 vCPU | 8 GiB |
| `DEV1-XL` | 4 vCPU | 12 GiB |

Source: Scaleway Instances datasheet.

## BASIC3 active profile reference

The syllabus requires one node with 16 vCPU. The DEV1 family cannot provide
that size because `DEV1-XL` has only 4 vCPU. For the active TP worker profile,
use a larger Scaleway instance type, for example:

| Type | vCPU | RAM | Usage |
| --- | ---: | ---: | --- |
| `BASIC3-X8C-32G` | 8 vCPU | 32 GiB | Recommended active master profile for TP |
| `BASIC3-X16C-32G` | 16 vCPU | 32 GiB | Recommended active worker profile for TP |

Keep the reduced mode on a smaller type such as `DEV1-L` when the platform is
idle or lightly used.

## Variables to change

### Worker CPU/RAM

Workers are the machines intended to be resized regularly.

Use:

```hcl
worker_mode = "active"
```

for full resources during TP sessions.

Use:

```hcl
worker_mode = "reduced"
```

outside TP sessions.

The two instance types are configured with:

```hcl
worker_active_commercial_type  = "DEV1-S"
worker_reduced_commercial_type = "DEV1-S"
```

Change these variables in `terraform.tfvars` if the validated Scaleway quote
uses different instance types.

Tiny example for testing the procedure at low cost:

```hcl
cluster_size                   = "tiny"
worker_mode                    = "active"
worker_active_commercial_type  = "DEV1-S"
worker_reduced_commercial_type = "DEV1-S"
```

Large example for the teaching cluster:

```hcl
cluster_size                   = "large"
worker_mode                    = "active"
worker_active_commercial_type  = "BASIC3-X16C-32G"
worker_reduced_commercial_type = "DEV1-L"
```

Then switch only the mode when moving between TP and off-TP periods:

```hcl
worker_mode = "reduced"
```

The important point is that `worker_mode`,
`worker_active_commercial_type` and `worker_reduced_commercial_type` are shared
by both profiles. This lets you test the same Terraform/Ansible resize
procedure in tiny mode before deploying it in large mode.

### Number of workers

The number of workers is controlled separately from CPU/RAM:

```hcl
tiny_worker_count  = 3
large_worker_count = 5
```

Changing the worker count adds or removes worker VMs. It is not the same as
resizing existing workers.

### Worker data disk size

Worker HDFS data disk size is also separate from CPU/RAM:

```hcl
large_worker_data_size_gb = 600
```

Increasing this value grows the attached Block Storage data volume. It does not
change CPU or RAM.

Do not decrease an existing HDFS data volume size.

### Gateway CPU/RAM

The gateway can also use active/reduced compute modes:

```hcl
gateway_mode                    = "active"
gateway_active_commercial_type  = "DEV1-L"
gateway_reduced_commercial_type = "DEV1-S"
```

By default, the active gateway type preserves the profile defaults: `DEV1-S`
for `tiny` and `DEV1-L` for `large`. The reduced gateway type defaults to
`DEV1-S`.

### Master CPU/RAM

The Hadoop master can also use active/reduced compute modes:

```hcl
master_mode                    = "active"
master_active_commercial_type  = "BASIC3-X8C-32G"
master_reduced_commercial_type = "DEV1-L"
```

By default, the active master type preserves the profile defaults: `DEV1-S`
for `tiny` and the documented 8 vCPU / 32 GiB master sizing with
`BASIC3-X8C-32G` for `large`. The reduced master type defaults to `DEV1-S` for
`tiny` and `DEV1-L` for `large`.

### Bastion CPU/RAM

Bastion instance types are still defined inside
`infra-hadoop/scaleway/terraform/main.tf` in the `server_profiles` local value.

For regular teaching operations, use `worker_mode`, `gateway_mode` and
`master_mode` to move the teaching platform between active and reduced compute
profiles. Change bastion sizing only after reviewing the `main.tf` profile
carefully.

## Resize procedure

Run the procedure from `infra-hadoop/scaleway`.

### 1. Stop Hadoop services cleanly

Before resizing VMs, stop Hadoop/Hive/HBase/Spark services:

```bash
cd ansible
ansible-playbook stop-services.yml
```

This stops services in a safe order:

- Hive services on the gateway;
- HBase services;
- Spark History Server;
- YARN services;
- HDFS DataNodes;
- HDFS NameNode.

Stopping services first avoids HDFS/YARN seeing machines disappear abruptly
during the VM resize or replacement.

### 2. Change Terraform variables

Edit:

```text
infra-hadoop/scaleway/terraform/terraform.tfvars
```

For full worker resources during TP:

```hcl
cluster_size = "large"
worker_mode  = "active"
gateway_mode = "active"
master_mode  = "active"
```

For reduced worker resources outside TP:

```hcl
cluster_size = "large"
worker_mode  = "reduced"
gateway_mode = "reduced"
master_mode  = "reduced"
```

If needed, adjust the instance types:

```hcl
worker_active_commercial_type  = "BASIC3-X16C-32G"
worker_reduced_commercial_type = "DEV1-L"
gateway_active_commercial_type  = "DEV1-L"
gateway_reduced_commercial_type = "DEV1-S"
master_active_commercial_type   = "BASIC3-X8C-32G"
master_reduced_commercial_type  = "DEV1-L"
```

Instead of editing `terraform.tfvars`, you can pass the same values as command
parameters. This is useful for temporary switches between active and reduced
mode.

Tiny active test:

```bash
terraform apply \
  -var='cluster_size=tiny' \
  -var='worker_mode=active' \
  -var='gateway_mode=active' \
  -var='master_mode=active' \
  -var='worker_active_commercial_type=DEV1-M' \
  -var='worker_reduced_commercial_type=DEV1-S'
```

Tiny reduced test:

```bash
terraform apply \
  -var='cluster_size=tiny' \
  -var='worker_mode=reduced' \
  -var='gateway_mode=reduced' \
  -var='master_mode=reduced' \
  -var='worker_active_commercial_type=DEV1-M' \
  -var='worker_reduced_commercial_type=DEV1-S'
```

Large active mode:

```bash
terraform apply \
  -var='cluster_size=large' \
  -var='worker_mode=active' \
  -var='gateway_mode=active' \
  -var='master_mode=active' \
  -var='worker_active_commercial_type=BASIC3-X16C-32G' \
  -var='worker_reduced_commercial_type=DEV1-L'
```

Large reduced mode:

```bash
terraform apply \
  -var='cluster_size=large' \
  -var='worker_mode=reduced' \
  -var='gateway_mode=reduced' \
  -var='master_mode=reduced' \
  -var='worker_active_commercial_type=BASIC3-X16C-32G' \
  -var='worker_reduced_commercial_type=DEV1-L'
```

### 3. Preview the Terraform change

Run this only after `ansible-playbook stop-services.yml` has completed
successfully.

```bash
cd terraform
terraform plan \
  -var='cluster_size=large' \
  -var='worker_mode=active' \
  -var='gateway_mode=active' \
  -var='master_mode=active' \
  -var='worker_active_commercial_type=BASIC3-X16C-32G' \
  -var='worker_reduced_commercial_type=DEV1-L'
```

Review the plan carefully.

Expected change for CPU/RAM resizing:

- worker, gateway and master instance types change if their mode changes;
- worker data volumes remain as separate `scaleway_block_volume` resources.

Be careful if Terraform shows data volume deletion. That is not expected for a
simple CPU/RAM resize.

### 4. Apply the resize

Run this only after the cluster services have been stopped.

```bash
terraform apply \
  -var='cluster_size=large' \
  -var='worker_mode=active' \
  -var='gateway_mode=active' \
  -var='master_mode=active' \
  -var='worker_active_commercial_type=BASIC3-X16C-32G' \
  -var='worker_reduced_commercial_type=DEV1-L'
```

Terraform manages infrastructure only. It does not restart Hadoop services
inside the VMs.

If Terraform recreates instances, regenerate the Ansible inventory:

```bash
terraform output -raw ansible_inventory > ../ansible/inventory.ini
```

If you run Ansible from the bastion, copy the updated inventory to the bastion
again.

### 5. Start services again

If Terraform recreated VMs or if you are unsure:

```bash
cd infra-hadoop/scaleway/ansible
ansible-playbook site.yml
```

`site.yml` is longer, but it reinstalls/reconfigures the nodes and is safer
after instance replacement.

If the machines were only resized and the OS configuration is still present:

```bash
cd infra-hadoop/scaleway/ansible
ansible-playbook start-services.yml
```


### 6. Verify the cluster

From the gateway:

```bash
source /etc/profile.d/hadoop.sh
source /etc/profile.d/spark.sh
source /etc/profile.d/hive.sh
source /etc/profile.d/hbase.sh
```

Check HDFS and YARN:

```bash
hdfs dfsadmin -report
yarn node -list
yarn application -list -appStates ALL
```

Check Hive and HBase:

```bash
beeline -u 'jdbc:hive2://localhost:10000/default;auth=noSasl' -e 'SHOW DATABASES;'
echo "status 'simple'" | hbase shell -n
```

Check the web UIs:

```text
NameNode UI:             http://<gateway_public_ip>:9870
YARN ResourceManager:    http://<gateway_public_ip>:8088
MapReduce HistoryServer: http://<gateway_public_ip>:19888
Spark History Server:    http://<gateway_public_ip>:18080
HiveServer2 Web UI:      http://<gateway_public_ip>:10002
HBase Master UI:         http://<gateway_public_ip>:16010
```

## Typical workflows

### Test the resize workflow with tiny

```bash
cd infra-hadoop/scaleway/ansible
ansible-playbook stop-services.yml

cd ../terraform
terraform apply \
  -var='cluster_size=tiny' \
  -var='worker_mode=active' \
  -var='gateway_mode=active' \
  -var='master_mode=active' \
  -var='worker_active_commercial_type=DEV1-S' \
  -var='worker_reduced_commercial_type=DEV1-S'
terraform output -raw ansible_inventory > ../ansible/inventory.ini

cd ../ansible
ansible-playbook start-services.yml
```

Then test the reduced mode with the same tiny profile:

```bash
cd infra-hadoop/scaleway/ansible
ansible-playbook stop-services.yml

cd ../terraform
terraform apply \
  -var='cluster_size=tiny' \
  -var='worker_mode=reduced' \
  -var='gateway_mode=reduced' \
  -var='master_mode=reduced' \
  -var='worker_active_commercial_type=DEV1-S' \
  -var='worker_reduced_commercial_type=DEV1-S'
terraform output -raw ansible_inventory > ../ansible/inventory.ini

cd ../ansible
ansible-playbook start-services.yml
```

### Before a TP session

```bash
cd infra-hadoop/scaleway/ansible
ansible-playbook stop-services.yml

cd ../terraform
terraform apply \
  -var='cluster_size=large' \
  -var='worker_mode=active' \
  -var='gateway_mode=active' \
  -var='master_mode=active' \
  -var='worker_active_commercial_type=BASIC3-X16C-32G' \
  -var='worker_reduced_commercial_type=DEV1-L'
terraform output -raw ansible_inventory > ../ansible/inventory.ini

cd ../ansible
ansible-playbook start-services.yml
```

### After a TP session

```bash
cd infra-hadoop/scaleway/ansible
ansible-playbook stop-services.yml

cd ../terraform
terraform apply \
  -var='cluster_size=large' \
  -var='worker_mode=reduced' \
  -var='gateway_mode=reduced' \
  -var='master_mode=reduced' \
  -var='worker_active_commercial_type=BASIC3-X16C-32G' \
  -var='worker_reduced_commercial_type=DEV1-L'
terraform output -raw ansible_inventory > ../ansible/inventory.ini

cd ../ansible
ansible-playbook start-services.yml
```

### If VMs were replaced

Use the full Ansible playbook instead of only `start-services.yml`:

```bash
cd infra-hadoop/scaleway/ansible
ansible-playbook site.yml
```

## Important notes

- CPU/RAM resize is controlled by Scaleway instance type, not by numeric CPU/RAM
  Terraform variables.
- Worker data disks are separate Block Storage volumes and should survive
  worker, gateway or master compute resizing.
- Stop Hadoop services before resizing.
- Run Ansible after Terraform. `terraform apply` does not start Hadoop, Hive,
  Spark or HBase services inside the machines.
- Do not use `terraform destroy` for a temporary resize. It is for final
  teardown and deletes the infrastructure.
