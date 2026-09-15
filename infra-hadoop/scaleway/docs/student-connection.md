# Student Connection

## Generate an SSH key

Run this command on your own computer:

```bash
ssh-keygen -t ed25519 -a 100 -f ~/.ssh/m2-hadoop-student -C studentXX
```

Replace `studentXX` with your assigned login, for example:

```bash
ssh-keygen -t ed25519 -a 100 -f ~/.ssh/m2-hadoop-student -C student02
```

## Send the public key

Display your public key:

```bash
cat ~/.ssh/m2-hadoop-student.pub
```

Send only this public key to the teacher.

Do not send the private key:

```text
~/.ssh/m2-hadoop-student
```

## Connect to the Hadoop gateway

After the teacher installs your public key, connect with:

```bash
ssh -i ~/.ssh/m2-hadoop-student studentXX@<gateway_public_ip>
```

Example:

```bash
ssh -i ~/.ssh/m2-hadoop-student student02@<gateway_public_ip>
```

## Load Hadoop and Spark commands

After login:

```bash
source /etc/profile.d/hadoop.sh
source /etc/profile.d/spark.sh
source /etc/profile.d/hive.sh
source /etc/profile.d/hbase.sh
```

Check Hadoop:

```bash
hdfs dfs -ls /
```

Check Spark:

```bash
spark-submit --version
```

Check Hive:

```bash
beeline --version
```

Check HBase:

```bash
hbase version
```
