#!/usr/bin/env bash
set -euo pipefail

for port in 9000 9870 9864 8088 8042 19888 18080 10000 10002 16010 16030; do
  nc -z localhost "$port" >/dev/null 2>&1
done

hdfs dfs -ls / >/dev/null 2>&1
