# Student Connection

For the complete exercise in French, see [TP 01](../../../tp/01-big-data-hadoop/README.md).

## Generate an SSH key

Run this command on your own computer:

```bash
ssh-keygen -t ed25519 -a 100 -f ~/.ssh/m2-hadoop-student -C nom.prenom
```

Replace `nom.prenom` with your username (surname.firstname), for example:

```bash
ssh-keygen -t ed25519 -a 100 -f ~/.ssh/m2-hadoop-student -C dupont.alice
```

If that key file already exists, reuse it or choose another filename instead
of overwriting it. Use the matching filename in the commands below.

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

Follow the automation's comment on your issue to the PR. After approval and
merge, the enabled bastion timer checks about every two minutes; the cluster
must be available. Merge alone does not confirm successful deployment.

To add another computer, submit its public key with the same username. Duplicate
keys are ignored; up to ten distinct keys per account are supported. Requests
never replace or revoke older keys. Contact the teacher if a key must be revoked
or another student has the same name.

For invalid fields, edit the issue, then close and reopen it to retry. Once a
PR exists, submit corrections through a new issue and ask the teacher to close
the superseded PR. The form is public: submit only the requested username and
public keys, without unnecessary personal data.

Do not send the private key:

```text
~/.ssh/m2-hadoop-student
```

## Connect to the Hadoop gateway

After the PR is merged and the key deployed, connect with the form's username:

```bash
ssh -i ~/.ssh/m2-hadoop-student nom.prenom@<gateway_public_ip>
```

Example:

```bash
ssh -i ~/.ssh/m2-hadoop-student dupont.alice@<gateway_public_ip>
```

The teacher provides `<gateway_public_ip>`. Run `whoami` after connecting and
check that it matches your requested username. For `Permission denied (publickey)`,
check the username, private key filename and PR status; if merged, ask the
teacher to inspect synchronization. Never send your private key for diagnosis.

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
