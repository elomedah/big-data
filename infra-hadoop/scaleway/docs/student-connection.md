# Student Connection

## Generate an SSH key

Run this command on your own computer:

```bash
ssh-keygen -t ed25519 -a 100 -f ~/.ssh/m2-hadoop-student -C studentXX
```

Replace `studentXX` with your username in `nom.prenom` format, for example:

```bash
ssh-keygen -t ed25519 -a 100 -f ~/.ssh/m2-hadoop-student -C dupont.alice
```

## Submit the public key

Display your public key:

```bash
cat ~/.ssh/m2-hadoop-student.pub
```

Open the public [Accès SSH au cluster form](https://github.com/elomedah/big-data/issues/new?template=student-access.yml)
using your GitHub account; no prior registration with the teacher is required.
Enter your username as `nom.prenom` (surname.firstname), for example
`dupont.alice`: lowercase letters without accents or spaces, exactly one dot,
32 characters maximum. Hyphens are allowed in compound names.
Paste the public key. The teacher reviews the generated pull request; after
merge, the bastion adds the approved keys. Existing keys are always retained.

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
ssh -i ~/.ssh/m2-hadoop-student dupont.alice@<gateway_public_ip>
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
