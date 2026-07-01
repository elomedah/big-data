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

## Run Ansible From The Bastion

Use this when Ansible is installed directly on the bastion.

From your local machine, prepare the bastion. This copies the whole
`hadoop/scaleway` project, installs the bastion inventory, and copies the
private SSH key needed to reach private nodes:

```bash
cd hadoop/scaleway/terraform
chmod +x prepare-bastion.sh
./prepare-bastion.sh
```

The script copies the project to:

```text
~/hadoop/scaleway
```

and installs the bastion inventory as:

```text
~/hadoop/scaleway/ansible/inventory.ini
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

## Hadoop Web Interfaces

In cloud mode, Hadoop web interfaces are not exposed publicly. Access them
through the gateway public IP, an SSH tunnel, or a SOCKS proxy via the bastion.

### Option 1: Gateway public IP

The Ansible `gateway_proxy` role installs Nginx on the gateway and exposes the
Hadoop web UIs through the gateway public IP.

First apply Terraform so the gateway security group opens the web UI ports:

```bash
cd hadoop/scaleway/terraform
terraform apply
```

Then rerun Ansible:

```bash
cd hadoop/scaleway/ansible
ansible-playbook site.yml
```

Get the gateway public IP:

```bash
cd hadoop/scaleway/terraform
terraform output -raw gateway_public_ip
```

Students can then open:

```text
NameNode UI:             http://<gateway_public_ip>:9870
YARN ResourceManager:    http://<gateway_public_ip>:8088
MapReduce HistoryServer: http://<gateway_public_ip>:19888
Worker 1 DataNode:       http://<gateway_public_ip>:9864
Worker 2 DataNode:       http://<gateway_public_ip>:9865
Worker 3 DataNode:       http://<gateway_public_ip>:9866
Worker 1 NodeManager:    http://<gateway_public_ip>:8042
Worker 2 NodeManager:    http://<gateway_public_ip>:8043
Worker 3 NodeManager:    http://<gateway_public_ip>:8044
```

### Option 2: SSH port forwarding

From your local machine:

```bash
ssh -i ~/.ssh/m2-hadoop-scaleway \
  -L 9870:10.42.0.12:9870 \
  -L 8088:10.42.0.12:8088 \
  -L 19888:10.42.0.12:19888 \
  -L 9864:10.42.0.21:9864 \
  -L 8042:10.42.0.21:8042 \
  ubuntu@<bastion_public_ip>
```

Then open these URLs locally:

```text
NameNode UI:          http://localhost:9870
YARN ResourceManager: http://localhost:8088
HistoryServer:        http://localhost:19888
Worker 1 DataNode:    http://localhost:9864
Worker 1 NodeManager: http://localhost:8042
```

For all workers, use different local ports:

```bash
ssh -i ~/.ssh/m2-hadoop-scaleway \
  -L 9870:10.42.0.12:9870 \
  -L 8088:10.42.0.12:8088 \
  -L 19888:10.42.0.12:19888 \
  -L 9864:10.42.0.21:9864 \
  -L 9865:10.42.0.22:9864 \
  -L 9866:10.42.0.23:9864 \
  -L 8042:10.42.0.21:8042 \
  -L 8043:10.42.0.22:8042 \
  -L 8044:10.42.0.23:8042 \
  ubuntu@<bastion_public_ip>
```

Then open:

```text
Worker 1 DataNode:    http://localhost:9864
Worker 2 DataNode:    http://localhost:9865
Worker 3 DataNode:    http://localhost:9866
Worker 1 NodeManager: http://localhost:8042
Worker 2 NodeManager: http://localhost:8043
Worker 3 NodeManager: http://localhost:8044
```

### Option 3: SOCKS proxy

This is more convenient because the browser can reach all private Hadoop URLs
through the bastion.

Start a SOCKS proxy:

```bash
ssh -i ~/.ssh/m2-hadoop-scaleway -D 1080 ubuntu@<bastion_public_ip>
```

Configure your browser to use:

```text
SOCKS host: localhost
SOCKS port: 1080
```

Then open the private URLs directly:

```text
NameNode UI:          http://10.42.0.12:9870
YARN ResourceManager: http://10.42.0.12:8088
HistoryServer:        http://10.42.0.12:19888
Worker 1 DataNode:    http://10.42.0.21:9864
Worker 2 DataNode:    http://10.42.0.22:9864
Worker 3 DataNode:    http://10.42.0.23:9864
Worker 1 NodeManager: http://10.42.0.21:8042
Worker 2 NodeManager: http://10.42.0.22:8042
Worker 3 NodeManager: http://10.42.0.23:8042
```

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

If the NameNode UI shows no DataNodes, the NameNode is running but no worker
has registered as a DataNode. From the bastion, check:

```bash
cd hadoop/scaleway/ansible
ansible workers -m shell -a "systemctl status hadoop-datanode --no-pager"
ansible workers -m shell -a "jps"
ansible masters -m shell -a "/opt/hadoop/bin/hdfs dfsadmin -report" -b
```

If the DataNode service is stopped, restart it:

```bash
ansible workers -m systemd -a "name=hadoop-datanode state=restarted" -b
```

If it still fails, inspect the logs:

```bash
ansible workers -m shell -a "journalctl -u hadoop-datanode -n 80 --no-pager" -b
ansible workers -m shell -a "ls -lah /data/hadoop/datanode /opt/hadoop/logs" -b
```

Common causes are:

- the playbook stopped before the Hadoop role started DataNode services;
- the data disk was not mounted on `/data/hadoop`;
- the DataNode cannot reach the NameNode on `10.42.0.12:9000`;
- the DataNode directory has wrong ownership.
- the NameNode rejects the DataNode because private IP reverse DNS is not
  available.

If logs show `DisallowedDatanodeException` and `hostname cannot be resolved`,
rerun the playbook. The Hadoop role disables strict DataNode hostname checking
and the common role writes cluster private hostnames to `/etc/hosts`.

If the DataNode web UI shows `Actor State = INIT_FAILED`, check for a
NameNode/DataNode cluster ID mismatch:

```bash
ansible workers -m shell -a "journalctl -u hadoop-datanode -n 120 --no-pager | grep -i 'clusterid\|incompatible\|failed'" -b
```

On a fresh test cluster, you can reset DataNode storage and restart the
DataNodes:

```bash
ansible workers -m systemd -a "name=hadoop-datanode state=stopped" -b
ansible workers -m shell -a "rm -rf /data/hadoop/datanode/current" -b
ansible workers -m file -a "path=/data/hadoop/datanode state=directory owner=hadoop group=hadoop mode=0755" -b
ansible workers -m systemd -a "name=hadoop-datanode state=started" -b
ansible masters -m shell -a "/opt/hadoop/bin/hdfs dfsadmin -report" -b
```

This deletes the worker block metadata and HDFS blocks. Use it only for a new
or disposable test cluster.

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
