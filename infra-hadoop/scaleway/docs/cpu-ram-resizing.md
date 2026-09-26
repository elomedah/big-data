# CPU and RAM resizing

CPU and RAM are controlled by the Scaleway instance type (`commercial_type`).
The master, worker nodes and gateway each have independent `active` / `reduced` modes.

## 1. Stop services

From the repository root:

```bash
cd infra-hadoop/scaleway/ansible
ansible-playbook stop-services.yml
```

Wait for successful completion before continuing.

## 2. Set sizes and modes

Edit `infra-hadoop/scaleway/terraform/terraform.tfvars`.
Example instance types for the large teaching cluster:

```hcl
master_active_commercial_type   = "BASIC3-X8C-32G"
master_reduced_commercial_type  = "DEV1-L"
worker_active_commercial_type   = "BASIC3-X16C-32G"
worker_reduced_commercial_type  = "DEV1-L"
gateway_active_commercial_type  = "DEV1-L"
gateway_reduced_commercial_type = "DEV1-S"
```

For TP sessions:

```hcl
master_mode  = "active"
worker_mode  = "active"
gateway_mode = "active"
```

Outside TP sessions:

```hcl
master_mode  = "reduced"
worker_mode  = "reduced"
gateway_mode = "reduced"
```

Change only the modes for the machines you want to resize. `worker_mode` applies
to all worker nodes. Keep `cluster_size`, worker counts and disk sizes unchanged.
For a tiny resize test, use `DEV1-M` for active types and `DEV1-S` for reduced types.

## 3. Review and apply

From the `ansible` directory used in step 1:

```bash
cd ../terraform
terraform plan -out=resize.tfplan
```

Check the instance type changes for the master, workers and gateway. Do not apply
if the plan deletes data volumes; review any VM replacements before proceeding.

```bash
terraform apply resize.tfplan
terraform output -raw ansible_inventory > ../ansible/inventory.ini
```

If running Ansible from the bastion, copy the updated inventory there too.

## 4. Restart services

```bash
cd ../ansible
ansible-playbook start-services.yml
```

If VMs were replaced, run `ansible-playbook site.yml` instead to reinstall and
configure services before starting them.

## 5. Verify from the gateway

```bash
source /etc/profile.d/hadoop.sh
source /etc/profile.d/hive.sh
source /etc/profile.d/hbase.sh

hdfs dfsadmin -report
yarn node -list
beeline -u 'jdbc:hive2://localhost:10000/default;auth=noSasl' -e 'SHOW DATABASES;'
echo "status 'simple'" | hbase shell -n
```
