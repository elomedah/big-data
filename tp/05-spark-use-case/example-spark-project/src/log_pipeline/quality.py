from pyspark.sql import functions as F


def split_valid_and_rejected(logs):
    is_valid = (
        F.col("event_timestamp").isNotNull()
        & F.col("app_id").isNotNull()
        & F.col("status_code").isNotNull()
        & F.col("response_time_ms").isNotNull()
        & F.col("app_name").isNotNull()
    )

    valid_logs = logs.filter(is_valid)
    rejected_logs = (
        logs
        .filter(~is_valid)
        .withColumn(
            "rejection_reason",
            F.when(F.col("event_timestamp").isNull(), "invalid_event_ts")
             .when(F.col("app_id").isNull(), "missing_app_id")
             .when(F.col("status_code").isNull(), "missing_status_code")
             .when(F.col("response_time_ms").isNull(), "missing_response_time_ms")
             .when(F.col("app_name").isNull(), "unknown_app_id")
             .otherwise("unknown_reason")
        )
    )

    return valid_logs, rejected_logs
