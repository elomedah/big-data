from pyspark.sql import functions as F

from log_pipeline.schemas import APP_REFERENCE_SCHEMA, APP_SLA_SCHEMA, LOG_SCHEMA


def read_logs(spark, base_path, year, month, day):
    path = f"{base_path}/raw/*/application_logs/year={year}/month={month}/day={day}"
    return (
        spark.read
        .option("header", True)
        .schema(LOG_SCHEMA)
        .csv(path)
        .withColumn("source_file", F.input_file_name())
        .withColumn("source_team", F.regexp_extract(F.col("source_file"), r"/raw/([^/]+)/", 1))
    )


def read_app_reference(spark, base_path):
    return (
        spark.read
        .option("header", True)
        .schema(APP_REFERENCE_SCHEMA)
        .csv(f"{base_path}/raw/referentials/app_reference.csv")
    )


def read_app_sla(spark, base_path):
    return (
        spark.read
        .option("header", True)
        .schema(APP_SLA_SCHEMA)
        .csv(f"{base_path}/raw/referentials/app_sla.csv")
    )


def write_dataset(df, path, output_format, partition_columns):
    writer = (
        df.write
        .mode("overwrite")
        .partitionBy(*partition_columns)
    )

    if output_format == "orc":
        writer.orc(path)
    else:
        writer.parquet(path)
