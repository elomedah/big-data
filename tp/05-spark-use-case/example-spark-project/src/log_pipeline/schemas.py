from pyspark.sql.types import IntegerType, StringType, StructField, StructType


LOG_SCHEMA = StructType([
    StructField("event_ts", StringType(), True),
    StructField("app_id", StringType(), True),
    StructField("env", StringType(), True),
    StructField("level", StringType(), True),
    StructField("status_code", IntegerType(), True),
    StructField("response_time_ms", IntegerType(), True),
    StructField("request_id", StringType(), True),
    StructField("message", StringType(), True),
])


APP_REFERENCE_SCHEMA = StructType([
    StructField("app_id", StringType(), True),
    StructField("app_name", StringType(), True),
    StructField("owner_team", StringType(), True),
    StructField("criticality", StringType(), True),
    StructField("business_domain", StringType(), True),
])


APP_SLA_SCHEMA = StructType([
    StructField("app_id", StringType(), True),
    StructField("max_response_time_ms", IntegerType(), True),
    StructField("sla_level", StringType(), True),
])
