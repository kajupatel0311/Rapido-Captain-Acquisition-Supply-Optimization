import pandas as pd

from src.config import EXTRACTION_TS


def basic_profile(df, name):
    result = {
        "dataset": name,
        "rows": len(df),
        "columns": len(df.columns),
        "duplicate_rows": int(df.duplicated().sum()),
        "total_nulls": int(df.isna().sum().sum()),
    }

    return result


def timestamp_profile(df, name, timestamp_column):
    if timestamp_column not in df.columns:
        return {
            "dataset": name,
            "timestamp_column": timestamp_column,
            "min_ts": None,
            "max_ts": None,
            "invalid_ts": None,
        }

    series = df[timestamp_column]

    return {
        "dataset": name,
        "timestamp_column": timestamp_column,
        "min_ts": series.min(),
        "max_ts": series.max(),
        "invalid_ts": int(series.isna().sum()),
    }


def categorical_profile(df, columns):
    rows = []

    for column in columns:
        if column not in df.columns:
            continue

        counts = (
            df[column]
            .value_counts(dropna=False)
            .reset_index()
        )

        counts.columns = [column, "count"]

        for _, row in counts.iterrows():
            rows.append(
                {
                    "column": column,
                    "value": row[column],
                    "count": row["count"],
                }
            )

    return pd.DataFrame(rows)


def audit_all(data):
    profile_rows = []

    timestamp_columns = {
        "captains": "signup_ts",
        "doc_events": "event_ts",
        "approvals": "decision_ts",
        "activation": "first_order_ts",
        "nudges": "sent_ts",
        "airport_hourly": "hour_ts",
        "airport_trips": "request_ts",
    }

    for name, df in data.items():
        profile_rows.append(
            basic_profile(df, name)
        )

        if name in timestamp_columns:
            profile_rows.append(
                timestamp_profile(
                    df,
                    name,
                    timestamp_columns[name],
                )
            )

    profile = pd.DataFrame(profile_rows)

    return profile


def referential_integrity_checks(data):
    captains = set(data["captains"]["captain_id"].dropna())

    checks = []

    for dataset_name in [
        "doc_events",
        "approvals",
        "activation",
        "nudges",
    ]:
        df = data[dataset_name]

        unknown_ids = (
            set(df["captain_id"].dropna())
            - captains
        )

        checks.append(
            {
                "dataset": dataset_name,
                "unknown_captain_ids": len(unknown_ids),
            }
        )

    return pd.DataFrame(checks)


def document_event_checks(doc_events):
    checks = []

    if "attempt_no" in doc_events.columns:
        invalid_attempts = (
            ~doc_events["attempt_no"].between(1, 3)
        ).sum()

        checks.append(
            {
                "check": "attempt_no_outside_1_to_3",
                "count": int(invalid_attempts),
            }
        )

    if "event_type" in doc_events.columns:
        valid_events = {
            "upload_success",
            "verification_pass",
            "verification_fail",
        }

        invalid_events = (
            ~doc_events["event_type"].isin(valid_events)
        ).sum()

        checks.append(
            {
                "check": "invalid_event_type",
                "count": int(invalid_events),
            }
        )

    return pd.DataFrame(checks)