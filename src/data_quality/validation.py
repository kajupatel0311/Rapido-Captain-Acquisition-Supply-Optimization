from pathlib import Path
import pandas as pd


CUTOFF_DATE = pd.Timestamp("2026-06-30 23:59:59")

VALID_VEHICLES = {
    "auto",
    "cab",
    "erickshaw",
}

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

VALID_APPROVAL_STATUSES = {
    "approved",
    "dropped_in_docs",
    "in_progress",
    "rejected",
}


def normalize_category(series):
    return (
        series.astype("string")
        .str.strip()
        .str.lower()
    )


def validate_required_columns(df, required_columns, dataset):
    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{dataset}.csv is missing required columns: "
            f"{missing}"
        )


def validate_captains(df):
    validate_required_columns(
        df,
        [
            "captain_id",
            "signup_date",
            "city",
            "vehicle_type",
            "acquisition_channel",
        ],
        "captains",
    )

    issues = []

    duplicate_ids = int(
        df["captain_id"].duplicated().sum()
    )

    if duplicate_ids:
        issues.append({
            "dataset": "captains",
            "issue": "duplicate_captain_id",
            "count": duplicate_ids,
        })

    signup = pd.to_datetime(
        df["signup_date"],
        errors="coerce",
    )

    invalid_dates = int(signup.isna().sum())

    if invalid_dates:
        issues.append({
            "dataset": "captains",
            "issue": "invalid_signup_date",
            "count": invalid_dates,
        })

    future_dates = int(
        (signup > CUTOFF_DATE).sum()
    )

    if future_dates:
        issues.append({
            "dataset": "captains",
            "issue": "signup_after_cutoff",
            "count": future_dates,
        })

    vehicles = normalize_category(
        df["vehicle_type"]
    )

    invalid_vehicles = int(
        (~vehicles.isin(VALID_VEHICLES)).sum()
    )

    if invalid_vehicles:
        issues.append({
            "dataset": "captains",
            "issue": "invalid_vehicle_type",
            "count": invalid_vehicles,
        })

    for column in [
        "city",
        "acquisition_channel",
    ]:
        null_count = int(
            df[column].isna().sum()
        )

        if null_count:
            issues.append({
                "dataset": "captains",
                "issue": f"missing_{column}",
                "count": null_count,
            })

    return issues


def validate_doc_events(df, captain_ids):
    validate_required_columns(
        df,
        [
            "captain_id",
            "doc_type",
            "event_type",
            "attempt_no",
        ],
        "doc_events",
    )

    issues = []

    orphan_count = int(
        (~df["captain_id"].isin(captain_ids)).sum()
    )

    if orphan_count:
        issues.append({
            "dataset": "doc_events",
            "issue": "orphan_captain_id",
            "count": orphan_count,
        })

    doc_types = (
        df["doc_type"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    invalid_docs = int(
        (~doc_types.isin(VALID_DOC_TYPES)).sum()
    )

    if invalid_docs:
        issues.append({
            "dataset": "doc_events",
            "issue": "invalid_document_type",
            "count": invalid_docs,
        })

    events = normalize_category(
        df["event_type"]
    )

    invalid_events = int(
        (~events.isin(VALID_DOC_EVENTS)).sum()
    )

    if invalid_events:
        issues.append({
            "dataset": "doc_events",
            "issue": "invalid_event_type",
            "count": invalid_events,
        })

    attempts = pd.to_numeric(
        df["attempt_no"],
        errors="coerce",
    )

    invalid_attempts = int(
        (attempts.isna() | (attempts < 1)).sum()
    )

    if invalid_attempts:
        issues.append({
            "dataset": "doc_events",
            "issue": "invalid_attempt_number",
            "count": invalid_attempts,
        })

    return issues


def validate_approvals(df, captain_ids):
    validate_required_columns(
        df,
        [
            "captain_id",
            "status",
        ],
        "approvals",
    )

    issues = []

    orphan_count = int(
        (~df["captain_id"].isin(captain_ids)).sum()
    )

    if orphan_count:
        issues.append({
            "dataset": "approvals",
            "issue": "orphan_captain_id",
            "count": orphan_count,
        })

    duplicate_count = int(
        df["captain_id"].duplicated().sum()
    )

    if duplicate_count:
        issues.append({
            "dataset": "approvals",
            "issue": "duplicate_captain_id",
            "count": duplicate_count,
        })

    statuses = normalize_category(
        df["status"]
    )

    invalid_statuses = int(
        (~statuses.isin(VALID_APPROVAL_STATUSES)).sum()
    )

    if invalid_statuses:
        issues.append({
            "dataset": "approvals",
            "issue": "invalid_approval_status",
            "count": invalid_statuses,
        })

    return issues


def validate_activation(df, captain_ids):
    validate_required_columns(
        df,
        ["captain_id"],
        "activation",
    )

    issues = []

    orphan_count = int(
        (~df["captain_id"].isin(captain_ids)).sum()
    )

    if orphan_count:
        issues.append({
            "dataset": "activation",
            "issue": "orphan_captain_id",
            "count": orphan_count,
        })

    return issues


def validate_airport_hourly(df):
    issues = []

    required = [
        "hour",
        "requests",
        "fulfilled",
        "unfulfilled",
        "online_captains",
    ]

    validate_required_columns(
        df,
        required,
        "airport_hourly",
    )

    for column in [
        "requests",
        "fulfilled",
        "unfulfilled",
        "online_captains",
    ]:
        values = pd.to_numeric(
            df[column],
            errors="coerce",
        )

        invalid = int(
            (values.isna() | (values < 0)).sum()
        )

        if invalid:
            issues.append({
                "dataset": "airport_hourly",
                "issue": f"invalid_{column}",
                "count": invalid,
            })

    hours = pd.to_numeric(
        df["hour"],
        errors="coerce",
    )

    invalid_hours = int(
        (
            hours.isna()
            | (hours < 0)
            | (hours > 23)
        ).sum()
    )

    if invalid_hours:
        issues.append({
            "dataset": "airport_hourly",
            "issue": "invalid_hour",
            "count": invalid_hours,
        })

    requests = pd.to_numeric(
        df["requests"],
        errors="coerce",
    )

    fulfilled = pd.to_numeric(
        df["fulfilled"],
        errors="coerce",
    )

    unfulfilled = pd.to_numeric(
        df["unfulfilled"],
        errors="coerce",
    )

    mismatch = int(
        (fulfilled + unfulfilled != requests).sum()
    )

    if mismatch:
        issues.append({
            "dataset": "airport_hourly",
            "issue": "request_fulfillment_mismatch",
            "count": mismatch,
        })

    return issues
