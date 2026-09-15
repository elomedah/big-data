from pyspark.sql import functions as F


def build_daily_app_metrics(logs):
    return (
        logs
        .groupBy("event_date", "app_id", "app_name", "owner_team", "criticality", "business_domain")
        .agg(
            F.count("*").alias("event_count"),
            F.sum(F.col("is_error").cast("int")).alias("error_count"),
            F.sum(F.col("is_warning").cast("int")).alias("warning_count"),
            F.avg("response_time_ms").alias("avg_response_time_ms"),
            F.max("response_time_ms").alias("max_response_time_ms"),
            F.sum(F.col("sla_breached").cast("int")).alias("sla_breach_count"),
        )
        .withColumn("error_rate", F.col("error_count") / F.col("event_count"))
    )


def build_daily_team_metrics(logs):
    return (
        logs
        .groupBy("event_date", "source_team")
        .agg(
            F.count("*").alias("event_count"),
            F.countDistinct("app_id").alias("application_count"),
            F.sum(F.col("is_error").cast("int")).alias("error_count"),
            F.avg("response_time_ms").alias("avg_response_time_ms"),
        )
    )
