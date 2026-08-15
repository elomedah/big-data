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
- Spark configured to submit jobs on YARN.
- Hive Metastore and HiveServer2 on the gateway.
- Student Linux accounts on the gateway.
- Student HDFS home directories and quotas.
- Service stop/start playbooks for maintenance and resize operations.
- A shutdown playbook to stop services and power off the cluster.

## Prerequisites

Terraform must be applied first from `../terraform`.

From `infra-hadoop/scaleway/terraform`:

```bash
terraform apply
```

Install required Ansible collections:

```bash
cd infra-hadoop/scaleway/ansible
ansible-galaxy collection install -r requirements.yml
```

The SSH key used by Ansible must match the Terraform variable:

```hcl
admin_ssh_public_key_path = "~/.ssh/m2-hadoop-scaleway.pub"
```

## Run Ansible From The Bastion

Use this when Ansible is installed directly on the bastion.

From your local machine, prepare the bastion. This copies the whole
`infra-hadoop/scaleway` project, installs the bastion inventory, and copies the
private SSH key needed to reach private nodes:

```bash
cd infra-hadoop/scaleway/terraform
chmod +x prepare-bastion.sh
./prepare-bastion.sh
```

The script copies the project to:

```text
~/infra-hadoop/scaleway
```

and installs the bastion inventory as:

```text
~/infra-hadoop/scaleway/ansible/inventory.ini
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
cd infra-hadoop/scaleway/ansible
ansible-galaxy collection install -r requirements.yml
ansible-playbook site.yml
```

## Spark On YARN

Spark is installed on the gateway, master and workers under:

```text
/opt/spark
```

The playbook also installs:

```text
/etc/profile.d/spark.sh
```

Students and teachers should submit Spark jobs from the gateway:

```bash
source /etc/profile.d/hadoop.sh
source /etc/profile.d/spark.sh
```

Run a first YARN test:

```bash
spark-submit \
  --master yarn \
  --deploy-mode client \
  --class org.apache.spark.examples.SparkPi \
  $SPARK_HOME/examples/jars/spark-examples_2.12-3.5.8.jar \
  10
```

Check the application in YARN:

```bash
yarn application -list
```

Then open the YARN ResourceManager UI:

```text
http://<gateway_public_ip>:8088
```

Spark event logs are stored in HDFS:

```text
/spark-logs
```

Spark runtime jars are stored in HDFS:

```text
/spark-jars
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
cd infra-hadoop/scaleway/terraform
terraform apply
```

Then rerun Ansible:

```bash
cd infra-hadoop/scaleway/ansible
ansible-playbook site.yml
```

Get the gateway public IP:

```bash
cd infra-hadoop/scaleway/terraform
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

## Stop And Start Services

Before resizing workers with Terraform, stop the cluster services cleanly:

```bash
ansible-playbook stop-services.yml
```

The stop playbook uses this order:

- gateway services: HiveServer2, Hive Metastore, Nginx;
- worker services: HBase RegionServer, YARN NodeManager, HDFS DataNode;
- master services: HBase Master, ZooKeeper, Spark History Server, MapReduce
  History Server, YARN ResourceManager, HDFS NameNode.

After the resize, either rerun the full configuration:

```bash
ansible-playbook site.yml
```

or restart only the services:

```bash
ansible-playbook start-services.yml
```

The start playbook uses the reverse dependency order: master services first,
then worker services, then gateway services.

## Shutdown The Cluster

Use the dedicated shutdown playbook to stop Hadoop services cleanly and power
off the machines.

From `infra-hadoop/scaleway/ansible`:

```bash
ansible-playbook shutdown.yml
```

By default, this shuts down:

- the gateway;
- the workers;
- the master.

The bastion stays up so you can still reconnect and operate the infrastructure.

To also shut down the bastion, run:

```bash
ansible-playbook shutdown.yml -e shutdown_bastion=true
```

If you run Ansible from the bastion itself, this last command will terminate
your SSH session once the bastion powers off.

After shutdown, verify the instance state in the Scaleway console. Block Storage
volumes, snapshots, Object Storage and reserved IPs can still generate costs
while the machines are powered off.
