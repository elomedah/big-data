from pyspark.sql import functions as F


def enrich_logs(logs):
    return (
        logs
        .withColumn("event_timestamp", F.to_timestamp("event_ts"))
        .withColumn("event_date", F.to_date("event_timestamp"))
        .withColumn("event_hour", F.hour("event_timestamp"))
        .withColumn("is_error", F.col("level") == F.lit("ERROR"))
        .withColumn("is_warning", F.col("level") == F.lit("WARN"))
        .withColumn(
            "latency_bucket",
            F.when(F.col("response_time_ms") < 300, "fast")
             .when(F.col("response_time_ms") < 1000, "medium")
             .otherwise("slow")
        )
    )


def join_referentials(logs, apps, sla):
    return (
        logs
        .join(F.broadcast(apps), on="app_id", how="left")
        .join(F.broadcast(sla), on="app_id", how="left")
        .withColumn("sla_breached", F.col("response_time_ms") > F.col("max_response_time_ms"))
    )
