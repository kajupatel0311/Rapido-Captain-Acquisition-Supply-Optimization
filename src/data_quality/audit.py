from pathlib import Path
import pandas as pd
import json


VALID_DOC_TYPES = {
    "DL",
    "RC",
    "AADHAAR",
    "PERMIT",
    "FITNESS",
    "INSURANCE",
}

VALID_DOC_EVENTS = {
    "upload_success",
    "verification_pass",
    "verification_fail",
}

VALID_VEHICLES = {
    "auto",
    "cab",
    "erickshaw",
}

VALID_APPROVAL_STATUSES = {
    "approved",
    "dropped_in_docs",
    "in_progress",
    "rejected",
}


def normalize_text(series):
    return (
        series.astype("string")
        .str.strip()
        .str.lower()
    )


def audit_captains(df):
    issues = []

    if "captain_id" not in df.columns:
        issues.append({
            "dataset": "captains",
            "issue": "missing_captain_id_column",
            "count": len(df),
        })
        return issues

    duplicate_ids = df["captain_id"].duplicated(keep=False).sum()

    if duplicate_ids:
        issues.append({
            "dataset": "captains",
            "issue": "duplicate_captain_id",
            "count": int(duplicate_ids),
        })

    if "signup_date" in df.columns:
        dates = pd.to_datetime(
            df["signup_date"],
            errors="coerce"
        )

        invalid_dates = dates.isna().sum()

        if invalid_dates:
            issues.append({
                "dataset": "captains",
                "issue": "invalid_signup_date",
                "count": int(invalid_dates),
            })

        future_dates = (
            dates > pd.Timestamp("2026-06-30 23:59:59")
        ).sum()

        if future_dates:
            issues.append({
                "dataset": "captains",
                "issue": "signup_after_cutoff",
                "count": int(future_dates),
            })

    if "vehicle_type" in df.columns:
        vehicle = normalize_text(df["vehicle_type"])

        invalid_vehicle = (~vehicle.isin(VALID_VEHICLES)).sum()

        if invalid_vehicle:
            issues.append({
                "dataset": "captains",
                "issue": "invalid_vehicle_type",
                "count": int(invalid_vehicle),
            })

    return issues


def audit_doc_events(df, captain_ids):
    issues = []

    if "captain_id" in df.columns:
        orphan_events = (
            ~df["captain_id"].isin(captain_ids)
        ).sum()

        if orphan_events:
            issues.append({
                "dataset": "doc_events",
                "issue": "captain_id_not_in_captains",
                "count": int(orphan_events),
            })

    if "doc_type" in df.columns:
        doc_types = normalize_text(df["doc_type"]).str.upper()

        invalid_docs = (
            ~doc_types.isin(VALID_DOC_TYPES)
        ).sum()

        if invalid_docs:
            issues.append({
                "dataset": "doc_events",
                "issue": "invalid_document_type",
                "count": int(invalid_docs),
            })

    if "event_type" in df.columns:
        event_types = normalize_text(df["event_type"])

        invalid_events = (
            ~event_types.isin(VALID_DOC_EVENTS)
        ).sum()

        if invalid_events:
            issues.append({
                "dataset": "doc_events",
                "issue": "invalid_event_type",
                "count": int(invalid_events),
            })

    if "attempt_no" in df.columns:
        attempts = pd.to_numeric(
            df["attempt_no"],
            errors="coerce"
        )

        invalid_attempts = (
            attempts.isna() | (attempts < 1)
        ).sum()

        if invalid_attempts:
            issues.append({
                "dataset": "doc_events",
                "issue": "invalid_attempt_number",
                "count": int(invalid_attempts),
            })

    return issues


def audit_approvals(df, captain_ids):
    issues = []

    if "captain_id" in df.columns:
        orphan = (~df["captain_id"].isin(captain_ids)).sum()

        if orphan:
            issues.append({
                "dataset": "approvals",
                "issue": "captain_id_not_in_captains",
                "count": int(orphan),
            })

        duplicate_ids = df["captain_id"].duplicated().sum()

        if duplicate_ids:
            issues.append({
                "dataset": "approvals",
                "issue": "duplicate_captain_id",
                "count": int(duplicate_ids),
            })

    if "status" in df.columns:
        status = normalize_text(df["status"])

        invalid_status = (
            ~status.isin(VALID_APPROVAL_STATUSES)
        ).sum()

        if invalid_status:
            issues.append({
                "dataset": "approvals",
                "issue": "invalid_approval_status",
                "count": int(invalid_status),
            })

    return issues


def audit_activation(df, captain_ids):
    issues = []

    if "captain_id" in df.columns:
        orphan = (~df["captain_id"].isin(captain_ids)).sum()

        if orphan:
            issues.append({
                "dataset": "activation",
                "issue": "captain_id_not_in_captains",
                "count": int(orphan),
            })

    return issues


def audit_airport_hourly(df):
    issues = []

    numeric_non_negative = [
        "requests",
        "fulfilled",
        "unfulfilled",
        "online_captains",
    ]

    for column in numeric_non_negative:
        if column not in df.columns:
            continue

        values = pd.to_numeric(
            df[column],
            errors="coerce"
        )

        invalid = (
            values.isna() | (values < 0)
        ).sum()

        if invalid:
            issues.append({
                "dataset": "airport_hourly",
                "issue": f"invalid_{column}",
                "count": int(invalid),
            })

    if "hour" in df.columns:
        hour = pd.to_numeric(
            df["hour"],
            errors="coerce"
        )

        invalid_hours = (
            hour.isna() |
            (hour < 0) |
            (hour > 23)
        ).sum()

        if invalid_hours:
            issues.append({
                "dataset": "airport_hourly",
                "issue": "invalid_hour",
                "count": int(invalid_hours),
            })

    if {
        "requests",
        "fulfilled",
        "unfulfilled",
    }.issubset(df.columns):

        requests = pd.to_numeric(
            df["requests"],
            errors="coerce"
        )

        fulfilled = pd.to_numeric(
            df["fulfilled"],
            errors="coerce"
        )

        unfulfilled = pd.to_numeric(
            df["unfulfilled"],
            errors="coerce"
        )

        mismatch = (
            fulfilled + unfulfilled != requests
        ).sum()

        if mismatch:
            issues.append({
                "dataset": "airport_hourly",
                "issue": "request_fulfillment_mismatch",
                "count": int(mismatch),
            })

    return issues


def run_data_quality_audit(data_dir):
    data_dir = Path(data_dir)

    captains = pd.read_csv(
        data_dir / "captains.csv"
    )

    doc_events = pd.read_csv(
        data_dir / "doc_events.csv"
    )

    approvals = pd.read_csv(
        data_dir / "approvals.csv"
    )

    activation = pd.read_csv(
        data_dir / "activation.csv"
    )

    airport_hourly = pd.read_csv(
        data_dir / "airport_hourly.csv"
    )

    all_issues = []

    all_issues.extend(
        audit_captains(captains)
    )

    captain_ids = set(
        captains["captain_id"].dropna()
    )

    all_issues.extend(
        audit_doc_events(
            doc_events,
            captain_ids
        )
    )

    all_issues.extend(
        audit_approvals(
            approvals,
            captain_ids
        )
    )

    all_issues.extend(
        audit_activation(
            activation,
            captain_ids
        )
    )

    all_issues.extend(
        audit_airport_hourly(
            airport_hourly
        )
    )

    report = {
        "datasets_checked": 5,
        "total_issues": len(all_issues),
        "issues": all_issues,
    }

    return report


if __name__ == "__main__":
    report = run_data_quality_audit(
        "data/raw"
    )

    Path("outputs/results").mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        "outputs/results/data_quality_report.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            report,
            f,
            indent=2
        )

    print(
        f"Data quality audit completed. "
        f"Issues found: {report['total_issues']}"
    )
    