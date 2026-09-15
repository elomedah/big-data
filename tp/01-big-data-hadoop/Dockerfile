FROM ubuntu:22.04

ARG HADOOP_VERSION=3.3.6
ARG SPARK_VERSION=3.5.8
ARG HIVE_VERSION=4.0.1
ARG HBASE_VERSION=2.5.15

ENV DEBIAN_FRONTEND=noninteractive \
    JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64 \
    HADOOP_HOME=/opt/hadoop \
    HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop \
    HADOOP_COMMON_HOME=/opt/hadoop \
    HADOOP_HDFS_HOME=/opt/hadoop \
    HADOOP_MAPRED_HOME=/opt/hadoop \
    YARN_HOME=/opt/hadoop \
    YARN_CONF_DIR=/opt/hadoop/etc/hadoop \
    SPARK_HOME=/opt/spark \
    SPARK_CONF_DIR=/opt/spark/conf \
    HIVE_HOME=/opt/hive \
    HIVE_CONF_DIR=/opt/hive/conf \
    HIVE_LOG_DIR=/var/log/hive \
    HIVE_PID_DIR=/data/hive \
    HBASE_HOME=/opt/hbase \
    HBASE_CONF_DIR=/opt/hbase/conf \
    HADOOP_HEAPSIZE=512 \
    HBASE_HEAPSIZE=512m \
    SPARK_DAEMON_MEMORY=512m \
    PATH=/opt/hadoop/bin:/opt/hadoop/sbin:/opt/spark/bin:/opt/spark/sbin:/opt/hive/bin:/opt/hbase/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libpostgresql-jdbc-java \
        nano \
        netcat-openbsd \
        openjdk-11-jdk \
        postgresql \
        postgresql-contrib \
        procps \
        python3 \
        rsync \
        tini \
        vim-tiny \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system hadoop \
    && useradd --system --create-home --gid hadoop --shell /bin/bash hadoop \
    && mkdir -p \
        /data \
        /run/hive \
        /var/log/hadoop \
        /var/log/hbase \
        /var/log/hive \
        /var/log/spark \
    && chown -R hadoop:hadoop \
        /data \
        /run/hive \
        /var/log/hadoop \
        /var/log/hbase \
        /var/log/hive \
        /var/log/spark

RUN mkdir -p "${HADOOP_HOME}" \
    && curl -fsSL "https://archive.apache.org/dist/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz" -o /tmp/hadoop.tar.gz \
    && tar -xzf /tmp/hadoop.tar.gz -C "${HADOOP_HOME}" --strip-components=1 \
    && rm /tmp/hadoop.tar.gz

RUN mkdir -p "${SPARK_HOME}" \
    && curl -fsSL "https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop3.tgz" -o /tmp/spark.tgz \
    && tar -xzf /tmp/spark.tgz -C "${SPARK_HOME}" --strip-components=1 \
    && rm /tmp/spark.tgz

RUN mkdir -p "${HIVE_HOME}" \
    && curl -fsSL "https://archive.apache.org/dist/hive/hive-${HIVE_VERSION}/apache-hive-${HIVE_VERSION}-bin.tar.gz" -o /tmp/hive.tar.gz \
    && tar -xzf /tmp/hive.tar.gz -C "${HIVE_HOME}" --strip-components=1 \
    && ln -sf /usr/share/java/postgresql.jar "${HIVE_HOME}/lib/postgresql-jdbc.jar" \
    && rm /tmp/hive.tar.gz

RUN mkdir -p "${HBASE_HOME}" \
    && curl -fsSL "https://archive.apache.org/dist/hbase/${HBASE_VERSION}/hbase-${HBASE_VERSION}-hadoop3-bin.tar.gz" -o /tmp/hbase.tar.gz \
    && tar -xzf /tmp/hbase.tar.gz -C "${HBASE_HOME}" --strip-components=1 \
    && find "${HBASE_HOME}/lib" -maxdepth 1 -type f -name 'hadoop-*.jar' -delete \
    && rm /tmp/hbase.tar.gz

COPY docker/config/hadoop/ ${HADOOP_CONF_DIR}/
COPY docker/config/spark/ ${SPARK_CONF_DIR}/
COPY docker/config/hive/ ${HIVE_CONF_DIR}/
COPY docker/config/hbase/ ${HBASE_CONF_DIR}/
COPY docker/profile.d/bigdata.sh /etc/profile.d/bigdata.sh
COPY docker/scripts/ /opt/tp-hadoop/bin/

RUN chmod +x /opt/tp-hadoop/bin/*.sh \
    && chown -R hadoop:hadoop \
        "${HADOOP_HOME}" \
        "${SPARK_HOME}" \
        "${HBASE_HOME}" \
        /opt/tp-hadoop \
    && chown -R hadoop:hadoop "${HIVE_CONF_DIR}"

EXPOSE 9000 9870 9864 9866 8088 8042 19888 18080 10000 10002 9083 16010 16030 2181 4040-4050

ENTRYPOINT ["/usr/bin/tini", "--", "/opt/tp-hadoop/bin/entrypoint.sh"]
CMD ["start"]
