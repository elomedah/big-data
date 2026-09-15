import argparse

from pyspark.sql import SparkSession

from log_pipeline.io import read_app_reference, read_app_sla, read_logs, write_dataset
from log_pipeline.metrics import build_daily_app_metrics, build_daily_team_metrics
from log_pipeline.quality import split_valid_and_rejected
from log_pipeline.transforms import enrich_logs, join_referentials


def parse_args():
    parser = argparse.ArgumentParser(description="Pipeline Spark de logs applicatifs")
    parser.add_argument("--base-path", required=True, help="Chemin HDFS du Data Lake utilisateur")
    parser.add_argument("--process-date", required=True, help="Date traitée au format YYYY-MM-DD")
    parser.add_argument(
        "--output-format",
        choices=["parquet", "orc"],
        default="parquet",
        help="Format de sortie pour les données traitées",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    spark = (
        SparkSession.builder
        .appName("tp05-structured-log-pipeline")
        .getOrCreate()
    )

    year, month, day = args.process_date.split("-")

    logs = read_logs(
        spark=spark,
        base_path=args.base_path,
        year=year,
        month=month,
        day=day,
    )
    apps = read_app_reference(spark, args.base_path)
    sla = read_app_sla(spark, args.base_path)

    enriched = enrich_logs(logs)
    joined = join_referentials(enriched, apps, sla)
    valid_logs, rejected_logs = split_valid_and_rejected(joined)

    daily_app_metrics = build_daily_app_metrics(valid_logs)
    daily_team_metrics = build_daily_team_metrics(valid_logs)

    write_dataset(
        df=valid_logs,
        path=f"{args.base_path}/processed/logs/events_{args.output_format}",
        output_format=args.output_format,
        partition_columns=["event_date", "app_id"],
    )
    write_dataset(
        df=daily_app_metrics,
        path=f"{args.base_path}/processed/logs/daily_app_metrics_{args.output_format}",
        output_format=args.output_format,
        partition_columns=["event_date", "app_id"],
    )
    write_dataset(
        df=daily_team_metrics,
        path=f"{args.base_path}/audit/spark/daily_team_metrics_{args.output_format}",
        output_format=args.output_format,
        partition_columns=["event_date"],
    )
    write_dataset(
        df=rejected_logs,
        path=f"{args.base_path}/audit/spark/rejected_logs_{args.output_format}",
        output_format=args.output_format,
        partition_columns=["source_team"],
    )

    print("Pipeline terminé")
    print(f"Logs valides : {valid_logs.count()}")
    print(f"Logs rejetés : {rejected_logs.count()}")

    spark.stop()


if __name__ == "__main__":
    main()
