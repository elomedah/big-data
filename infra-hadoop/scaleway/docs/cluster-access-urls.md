# Hadoop Cluster Access URLs

Replace `<gateway_public_ip>` with the gateway public IP given by the teacher.

## Main Web Interfaces

```text
NameNode UI:             http://<gateway_public_ip>:9870
YARN ResourceManager:    http://<gateway_public_ip>:8088
MapReduce HistoryServer: http://<gateway_public_ip>:19888
Spark History Server:    http://<gateway_public_ip>:18080
HiveServer2 Web UI:      http://<gateway_public_ip>:10002
HBase Master UI:         http://<gateway_public_ip>:16010
```

## Worker Web Interfaces

```text
Worker 1 DataNode:       http://<gateway_public_ip>:9864
Worker 2 DataNode:       http://<gateway_public_ip>:9865
Worker 3 DataNode:       http://<gateway_public_ip>:9866
```

```text
Worker 1 NodeManager:    http://<gateway_public_ip>:8042
Worker 2 NodeManager:    http://<gateway_public_ip>:8043
Worker 3 NodeManager:    http://<gateway_public_ip>:8044
```

```text
Worker 1 HBase RegionServer: http://<gateway_public_ip>:16030
Worker 2 HBase RegionServer: http://<gateway_public_ip>:16031
Worker 3 HBase RegionServer: http://<gateway_public_ip>:16032
```

## Spark Live UI

Spark live UI is available only while a Spark application is running.

```text
Spark live UI:           http://<gateway_public_ip>:4040
```

If several Spark applications run at the same time, Spark can use:

```text
http://<gateway_public_ip>:4041
http://<gateway_public_ip>:4042
...
http://<gateway_public_ip>:4050
```

For finished Spark applications, use:

```text
Spark History Server:    http://<gateway_public_ip>:18080
```

## Command Line Checks

Run these commands from the gateway:

```bash
source /etc/profile.d/hadoop.sh
source /etc/profile.d/spark.sh
source /etc/profile.d/hbase.sh
```

```bash
hdfs dfsadmin -report
yarn application -list -appStates ALL
hbase shell
```

View YARN logs:

```bash
yarn logs -applicationId <application_id>
```

Connect to Hive from the gateway:

```bash
beeline -u 'jdbc:hive2://localhost:10000/default;auth=noSasl' -n $USER --hivevar student=$USER
```
