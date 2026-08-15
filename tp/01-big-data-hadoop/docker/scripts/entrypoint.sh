#!/usr/bin/env bash
set -euo pipefail

export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export HADOOP_HOME=/opt/hadoop
export HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
export HADOOP_COMMON_HOME=/opt/hadoop
export HADOOP_HDFS_HOME=/opt/hadoop
export HADOOP_MAPRED_HOME=/opt/hadoop
export YARN_HOME=/opt/hadoop
export YARN_CONF_DIR=/opt/hadoop/etc/hadoop
export SPARK_HOME=/opt/spark
export SPARK_CONF_DIR=/opt/spark/conf
export HIVE_HOME=/opt/hive
export HIVE_CONF_DIR=/opt/hive/conf
export HBASE_HOME=/opt/hbase
export HBASE_CONF_DIR=/opt/hbase/conf
export PATH=/opt/hadoop/bin:/opt/hadoop/sbin:/opt/spark/bin:/opt/spark/sbin:/opt/hive/bin:/opt/hbase/bin:$PATH

run_as_hadoop() {
  runuser -u hadoop -- bash -lc "$*"
}

wait_for_port() {
  local host="$1"
  local port="$2"
  local label="$3"

  for _ in {1..90}; do
    if nc -z "$host" "$port" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done

  echo "Timed out waiting for ${label} on ${host}:${port}" >&2
  return 1
}

wait_for_hdfs() {
  for _ in {1..90}; do
    if run_as_hadoop "hdfs dfsadmin -report >/dev/null 2>&1"; then
      return 0
    fi
    sleep 2
  done

  echo "Timed out waiting for HDFS" >&2
  return 1
}

prepare_runtime_dirs() {
  mkdir -p \
    /data/hadoop/namenode \
    /data/hadoop/datanode \
    /data/hadoop/pids \
    /data/hadoop/tmp \
    /data/hadoop/yarn/local \
    /data/hadoop/yarn/logs \
    /data/hbase/pids \
    /data/hbase/tmp \
    /data/hbase/zookeeper \
    /data/hive \
    /data/spark/pids \
    /run/hive \
    /var/log/hadoop \
    /var/log/hbase \
    /var/log/hive \
    /var/log/spark

  chown -R hadoop:hadoop \
    /data \
    /run/hive \
    /var/log/hadoop \
    /var/log/hbase \
    /var/log/hive \
    /var/log/spark

  find /data/hadoop/pids /data/hbase/pids /data/hive /data/spark/pids -name "*.pid" -delete
}

start_postgres() {
  service postgresql start >/dev/null
  wait_for_port localhost 5432 PostgreSQL

  if ! runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='hive'" | grep -q 1; then
    runuser -u postgres -- psql -c "CREATE ROLE hive WITH LOGIN PASSWORD 'hive';"
  fi

  if ! runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_database WHERE datname='hive_metastore'" | grep -q 1; then
    runuser -u postgres -- createdb -O hive hive_metastore
  fi
}

format_hdfs_if_needed() {
  if [[ ! -f /data/hadoop/namenode/current/VERSION ]]; then
    run_as_hadoop "hdfs namenode -format -force -nonInteractive -clusterId tp01"
  fi
}

start_hadoop() {
  run_as_hadoop "hdfs --daemon start namenode"
  wait_for_port localhost 9000 "HDFS NameNode RPC"

  run_as_hadoop "hdfs --daemon start datanode"
  wait_for_hdfs

  run_as_hadoop "yarn --daemon start resourcemanager"
  wait_for_port localhost 8088 "YARN ResourceManager"

  run_as_hadoop "yarn --daemon start nodemanager"
  wait_for_port localhost 8042 "YARN NodeManager"

  run_as_hadoop "mapred --daemon start historyserver"
  wait_for_port localhost 19888 "MapReduce HistoryServer"
}

prepare_hdfs_layout() {
  run_as_hadoop "hdfs dfs -mkdir -p /tmp /tmp/hive /tmp/logs /user/hadoop /user/hive/warehouse /spark-logs /hbase"
  run_as_hadoop "hdfs dfs -chmod 1777 /tmp /tmp/hive /tmp/logs /spark-logs /user/hive/warehouse"
  run_as_hadoop "hdfs dfs -chown -R hadoop:hadoop /user/hadoop /spark-logs /hbase"
  run_as_hadoop "hdfs dfs -chown -R hadoop:hadoop /user/hive"
}

init_hive_schema_if_needed() {
  if ! PGPASSWORD=hive psql -h localhost -U hive -d hive_metastore -tAc "SELECT 1 FROM information_schema.tables WHERE lower(table_name)='version'" | grep -q 1; then
    run_as_hadoop "schematool -dbType postgres -initSchema"
  fi
}

start_spark() {
  run_as_hadoop "start-history-server.sh"
  wait_for_port localhost 18080 "Spark History Server"
}

start_hive() {
  run_as_hadoop "nohup hive --service metastore > /var/log/hive/metastore.log 2>&1 & echo \$! > /data/hive/metastore.pid"
  wait_for_port localhost 9083 "Hive Metastore"

  run_as_hadoop "nohup hive --service hiveserver2 > /var/log/hive/hiveserver2.log 2>&1 & echo \$! > /data/hive/hiveserver2.pid"
  wait_for_port localhost 10000 HiveServer2
  wait_for_port localhost 10002 "HiveServer2 Web UI"
}

start_hbase() {
  run_as_hadoop "hbase-daemon.sh start zookeeper"
  wait_for_port localhost 2181 "HBase ZooKeeper"

  run_as_hadoop "hbase-daemon.sh start master"
  wait_for_port localhost 16010 "HBase Master UI"

  run_as_hadoop "hbase-daemon.sh start regionserver"
  wait_for_port localhost 16030 "HBase RegionServer UI"
}

stop_pid_file() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    kill "$(cat "$pid_file")" >/dev/null 2>&1 || true
    rm -f "$pid_file"
  fi
}

stop_services() {
  set +e
  run_as_hadoop "hbase-daemon.sh stop regionserver"
  run_as_hadoop "hbase-daemon.sh stop master"
  run_as_hadoop "hbase-daemon.sh stop zookeeper"
  stop_pid_file /data/hive/hiveserver2.pid
  stop_pid_file /data/hive/metastore.pid
  run_as_hadoop "stop-history-server.sh"
  run_as_hadoop "mapred --daemon stop historyserver"
  run_as_hadoop "yarn --daemon stop nodemanager"
  run_as_hadoop "yarn --daemon stop resourcemanager"
  run_as_hadoop "hdfs --daemon stop datanode"
  run_as_hadoop "hdfs --daemon stop namenode"
  service postgresql stop >/dev/null 2>&1 || true
}

print_ready_message() {
  cat <<'EOF'

TP Hadoop all-in-one is ready.

Web UIs:
  HDFS NameNode:          http://localhost:9870
  HDFS DataNode:          http://localhost:9864
  YARN ResourceManager:   http://localhost:8088
  YARN NodeManager:       http://localhost:8042
  MapReduce History:      http://localhost:19888
  Spark History:          http://localhost:18080
  HiveServer2 Web UI:     http://localhost:10002
  HBase Master:           http://localhost:16010
  HBase RegionServer:     http://localhost:16030

Shell:
  docker exec -it tp-hadoop bash

EOF
}

start_all() {
  prepare_runtime_dirs
  start_postgres
  format_hdfs_if_needed
  start_hadoop
  prepare_hdfs_layout
  init_hive_schema_if_needed
  start_spark
  start_hive
  start_hbase
  print_ready_message
}

if [[ "${1:-start}" != "start" ]]; then
  exec "$@"
fi

trap 'stop_services; exit 0' INT TERM

start_all

while true; do
  sleep 3600 &
  wait $!
done
