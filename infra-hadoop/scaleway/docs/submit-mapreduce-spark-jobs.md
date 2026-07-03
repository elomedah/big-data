# Submit MapReduce And Spark Jobs

Run all commands from the gateway after connecting with SSH.

```bash
source /etc/profile.d/hadoop.sh
source /etc/profile.d/spark.sh
source /etc/profile.d/hive.sh
```

## Prepare HDFS Input

Create a local input file:

```bash
cat > input.txt <<'EOF'
hadoop spark hadoop
spark yarn hdfs
big data hadoop
EOF
```

Create an HDFS input directory:

```bash
hdfs dfs -mkdir -p /user/$USER/input
hdfs dfs -put -f input.txt /user/$USER/input/
hdfs dfs -ls /user/$USER/input
```

## Submit A MapReduce Streaming Job

Create the mapper:

```bash
cat > mapper.py <<'EOF'
#!/usr/bin/env python3
import sys

for line in sys.stdin:
    for word in line.strip().split():
        print(f"{word}\t1")
EOF
```

Create the reducer:

```bash
cat > reducer.py <<'EOF'
#!/usr/bin/env python3
import sys

current_word = None
current_count = 0

for line in sys.stdin:
    word, count = line.strip().split("\t", 1)
    count = int(count)
    if current_word == word:
        current_count += count
    else:
        if current_word is not None:
            print(f"{current_word}\t{current_count}")
        current_word = word
        current_count = count

if current_word is not None:
    print(f"{current_word}\t{current_count}")
EOF
```

Make scripts executable:

```bash
chmod +x mapper.py reducer.py
```

Remove previous output if needed:

```bash
hdfs dfs -rm -r -f /user/$USER/output-mapreduce
```

Submit the job:

```bash
hadoop jar $HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming-3.3.6.jar \
  -files mapper.py,reducer.py \
  -mapper mapper.py \
  -reducer reducer.py \
  -input /user/$USER/input \
  -output /user/$USER/output-mapreduce
```

Read the result:

```bash
hdfs dfs -cat /user/$USER/output-mapreduce/part-*
```

## Submit A Spark Python Job On YARN

Create the Spark job:

```bash
cat > wordcount.py <<'EOF'
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("student-wordcount").getOrCreate()
sc = spark.sparkContext

lines = sc.textFile("/user/" + sc.sparkUser() + "/input")
counts = (
    lines.flatMap(lambda line: line.split())
    .map(lambda word: (word, 1))
    .reduceByKey(lambda a, b: a + b)
)

output = "/user/" + sc.sparkUser() + "/output-spark"
counts.saveAsTextFile(output)

spark.stop()
EOF
```

Remove previous output if needed:

```bash
hdfs dfs -rm -r -f /user/$USER/output-spark
```

Submit the Spark job:

```bash
spark-submit \
  --master yarn \
  --deploy-mode client \
  wordcount.py
```

Read the result:

```bash
hdfs dfs -cat /user/$USER/output-spark/part-*
```

## Submit The Spark Pi Example

```bash
spark-submit \
  --master yarn \
  --deploy-mode client \
  --class org.apache.spark.examples.SparkPi \
  $SPARK_HOME/examples/jars/spark-examples_2.12-3.5.8.jar \
  10
```

## Run A Hive Query

Connect to HiveServer2:

```bash
beeline -u 'jdbc:hive2://localhost:10000/default;auth=noSasl' -n $USER
```

Create a database and an external table:

```sql
CREATE DATABASE IF NOT EXISTS student;
USE student;

DROP TABLE IF EXISTS words;

CREATE EXTERNAL TABLE words (
  line STRING
)
STORED AS TEXTFILE
LOCATION '/user/${env:USER}/input';

SELECT * FROM words;
```

Exit Beeline:

```sql
!quit
```

## Follow Applications

List applications:

```bash
yarn application -list -appStates ALL
```

Read logs:

```bash
yarn logs -applicationId <application_id>
```

Open the web interfaces:

```text
YARN ResourceManager: http://<gateway_public_ip>:8088
Spark History Server: http://<gateway_public_ip>:18080
```
