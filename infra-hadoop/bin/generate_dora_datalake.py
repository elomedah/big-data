import argparse
import csv
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path


TEAMS = [
    ("team_payments", "Payments", "finance", "Paris"),
    ("team_identity", "Identity", "security", "Lyon"),
    ("team_risk", "Risk", "risk", "London"),
    ("team_mobile", "Mobile", "digital", "Madrid"),
    ("team_support", "Support", "operations", "Warsaw"),
    ("team_data", "Data Platform", "platform", "Paris"),
]

TEAM_BUDGETS = {
    "team_payments": (1250000, 380000, 420000, 180000),
    "team_identity": (980000, 260000, 360000, 220000),
    "team_risk": (1420000, 410000, 520000, 300000),
    "team_mobile": (860000, 210000, 300000, 120000),
    "team_support": (640000, 150000, 180000, 90000),
    "team_data": (1550000, 520000, 610000, 240000),
}

APPLICATIONS = [
    ("payment-api", "Payment API", "team_payments", "critical", "java", "tier_1"),
    ("billing-worker", "Billing Worker", "team_payments", "high", "python", "tier_2"),
    ("auth-service", "Auth Service", "team_identity", "critical", "java", "tier_1"),
    ("identity-portal", "Identity Portal", "team_identity", "medium", "nodejs", "tier_2"),
    ("risk-engine", "Risk Engine", "team_risk", "critical", "scala", "tier_1"),
    ("fraud-detector", "Fraud Detector", "team_risk", "high", "python", "tier_1"),
    ("mobile-backend", "Mobile Backend", "team_mobile", "high", "go", "tier_2"),
    ("notification-api", "Notification API", "team_mobile", "medium", "nodejs", "tier_3"),
    ("ticketing-api", "Ticketing API", "team_support", "medium", "java", "tier_3"),
    ("crm-sync", "CRM Sync", "team_support", "low", "python", "tier_3"),
    ("datalake-ingest", "Datalake Ingest", "team_data", "high", "scala", "tier_2"),
    ("metrics-api", "Metrics API", "team_data", "medium", "go", "tier_2"),
]

SERVICES = [
    ("checkout", "/checkout", "customer"),
    ("refund", "/refund", "backoffice"),
    ("login", "/login", "customer"),
    ("token", "/token", "system"),
    ("score", "/risk/score", "system"),
    ("fraud-check", "/fraud/check", "system"),
    ("push", "/notifications/push", "customer"),
    ("email", "/notifications/email", "system"),
    ("ticket", "/tickets", "backoffice"),
    ("sync", "/sync", "system"),
    ("ingest", "/ingest", "system"),
    ("metrics", "/metrics", "backoffice"),
]

REGIONS = ["eu-west-1", "eu-west-3", "eu-central-1"]
ENVS = ["prod", "prod", "prod", "preprod"]
CHANNELS = ["web", "mobile", "api", "batch"]
DEPENDENCIES = ["postgres", "redis", "kafka", "hdfs", "partner_api", "none"]
ERROR_CODES = ["", "", "", "", "TIMEOUT", "VALIDATION_ERROR", "HTTP_500", "DEPENDENCY_DOWN"]


def parse_args():
    parser = argparse.ArgumentParser(description="Generate DORA training data")
    parser.add_argument("--output", required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--days", type=int, default=31)
    parser.add_argument("--events-per-day", type=int, default=50000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def write_csv(path, rows, header):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def build_referentials(base):
    teams_rows = [(team_id, name, domain, location) for team_id, name, domain, location in TEAMS]
    budget_rows = []
    apps_rows = []
    sla_rows = []
    service_rows = []
    deployments_rows = []

    for team_id, _, domain, _ in TEAMS:
        annual_budget, cloud_budget, run_budget, compliance_budget = TEAM_BUDGETS[team_id]
        budget_rows.append(
            (
                team_id,
                "2026",
                "EUR",
                annual_budget,
                cloud_budget,
                run_budget,
                compliance_budget,
                round(run_budget / annual_budget, 4),
                domain,
            )
        )

    for index, (app_id, app_name, team_id, criticality, runtime, tier) in enumerate(APPLICATIONS):
        sla_ms = {"critical": 250, "high": 500, "medium": 900, "low": 1500}[criticality]
        apps_rows.append((app_id, app_name, team_id, criticality, runtime, tier, random.choice(REGIONS)))
        sla_rows.append((app_id, sla_ms, 99.5 if criticality == "critical" else 99.0, 60, 15))

        service_name, endpoint, audience = SERVICES[index % len(SERVICES)]
        service_rows.append((service_name, app_id, endpoint, audience, criticality))

        for deploy_idx in range(1, 5):
            deployments_rows.append(
                (
                    f"dep-{app_id}-{deploy_idx:03d}",
                    app_id,
                    f"v{deploy_idx}.{index % 7}.{random.randint(0, 9)}",
                    f"2026-01-{deploy_idx * 5:02d}T09:00:00",
                    random.choice(["blue_green", "rolling", "canary"]),
                )
            )

    ref = base / "reference"
    write_csv(ref / "teams" / "teams.csv", teams_rows, ["team_id", "team_name", "domain", "location"])
    write_csv(
        ref / "team_budgets" / "team_budgets.csv",
        budget_rows,
        [
            "team_id",
            "budget_year",
            "currency",
            "annual_budget",
            "cloud_budget",
            "run_budget",
            "compliance_budget",
            "run_budget_ratio",
            "budget_domain",
        ],
    )
    write_csv(
        ref / "applications" / "applications.csv",
        apps_rows,
        ["app_id", "app_name", "team_id", "criticality", "runtime", "tier", "primary_region"],
    )
    write_csv(ref / "services" / "services.csv", service_rows, ["service_name", "app_id", "endpoint", "audience", "criticality"])
    write_csv(ref / "sla_contracts" / "sla_contracts.csv", sla_rows, ["app_id", "sla_ms", "availability_target", "rto_minutes", "rpo_minutes"])
    write_csv(
        ref / "deployments" / "deployments.csv",
        deployments_rows,
        ["deployment_id", "app_id", "build_version", "deployed_at", "strategy"],
    )
    return {row[0]: row for row in apps_rows}, {row[0]: row for row in sla_rows}, deployments_rows


def generate_logs(base, start_date, days, events_per_day, apps_by_id, sla_by_app, deployments):
    app_ids = list(apps_by_id.keys())
    deployments_by_app = {}
    for row in deployments:
        deployments_by_app.setdefault(row[1], []).append(row)

    header = [
        "event_id",
        "event_ts",
        "event_date",
        "event_hour",
        "app_id",
        "team_id",
        "service_name",
        "environment",
        "region",
        "endpoint",
        "event_type",
        "severity",
        "status_code",
        "response_time_ms",
        "bytes_in",
        "bytes_out",
        "request_id",
        "trace_id",
        "session_id",
        "user_type",
        "channel",
        "dependency",
        "deployment_id",
        "build_version",
        "host",
        "pod_name",
        "retry_count",
        "error_code",
        "is_sla_breach",
        "message",
    ]

    for day_offset in range(days):
        current_date = start_date + timedelta(days=day_offset)
        day_rows = []
        for event_index in range(events_per_day):
            app_id = random.choice(app_ids)
            app = apps_by_id[app_id]
            sla_ms = int(sla_by_app[app_id][1])
            service_name, endpoint, _ = SERVICES[APPLICATIONS.index(next(item for item in APPLICATIONS if item[0] == app_id)) % len(SERVICES)]
            event_dt = current_date + timedelta(seconds=random.randint(0, 86399))
            status_code = random.choices([200, 201, 204, 400, 401, 404, 429, 500, 502, 503], [65, 8, 7, 4, 3, 3, 2, 4, 2, 2])[0]
            severity = "ERROR" if status_code >= 500 else "WARN" if status_code >= 400 else "INFO"
            response_time = max(5, int(random.gauss(sla_ms * 0.75, sla_ms * 0.35)))
            if status_code >= 500:
                response_time += random.randint(sla_ms, sla_ms * 5)
            deploy = random.choice(deployments_by_app[app_id])
            error_code = random.choice(ERROR_CODES) if status_code >= 400 else ""
            is_sla_breach = response_time > sla_ms
            request_id = f"req-{current_date.strftime('%Y%m%d')}-{event_index:08d}"
            day_rows.append(
                (
                    str(uuid.uuid4()),
                    event_dt.isoformat(timespec="seconds"),
                    current_date.strftime("%Y-%m-%d"),
                    event_dt.strftime("%H"),
                    app_id,
                    app[2],
                    service_name,
                    random.choice(ENVS),
                    random.choice(REGIONS),
                    endpoint,
                    random.choice(["http_request", "job_step", "dependency_call", "business_event"]),
                    severity,
                    status_code,
                    response_time,
                    random.randint(100, 20000),
                    random.randint(200, 50000),
                    request_id,
                    f"trace-{random.randint(1, 999999):06d}",
                    f"sess-{random.randint(1, 200000):06d}",
                    random.choice(["customer", "employee", "service_account", "anonymous"]),
                    random.choice(CHANNELS),
                    random.choice(DEPENDENCIES),
                    deploy[0],
                    deploy[2],
                    f"host-{random.randint(1, 80):03d}",
                    f"pod-{app_id}-{random.randint(1, 12):02d}",
                    random.randint(0, 3),
                    error_code,
                    str(is_sla_breach).lower(),
                    f"{severity} on {app_id} {endpoint}",
                )
            )

        partition = base / "raw" / "application_logs" / f"year={current_date:%Y}" / f"month={current_date:%m}" / f"day={current_date:%d}"
        write_csv(partition / "application_logs.csv", day_rows, header)


def main():
    args = parse_args()
    random.seed(args.seed)
    output = Path(args.output)
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    apps_by_id, sla_by_app, deployments = build_referentials(output)
    generate_logs(output, start_date, args.days, args.events_per_day, apps_by_id, sla_by_app, deployments)
    print(f"Generated {args.days * args.events_per_day} events in {output}")


if __name__ == "__main__":
    main()
