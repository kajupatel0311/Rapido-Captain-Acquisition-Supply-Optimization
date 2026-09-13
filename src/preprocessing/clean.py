from pathlib import Path

import pandas as pd


CUTOFF_DATE = pd.Timestamp(
    "2026-06-30 23:59:59"
)


def clean_captains(df):
    """
    Clean captain signup data.

    Raw captain data uses signup_ts as the signup timestamp.
    signup_date is created as the standardized datetime field
    used by downstream analysis.
    """

    df = df.copy()

    # --------------------------------------------------------
    # Captain ID
    # --------------------------------------------------------

    if "captain_id" in df.columns:
        df["captain_id"] = (
            df["captain_id"]
            .astype("string")
            .str.strip()
        )

    # --------------------------------------------------------
    # City
    # --------------------------------------------------------

    if "city" in df.columns:
        df["city"] = (
            df["city"]
            .astype("string")
            .str.strip()
        )

    # --------------------------------------------------------
    # Vehicle type
    # --------------------------------------------------------

    if "vehicle_type" in df.columns:
        df["vehicle_type"] = (
            df["vehicle_type"]
            .astype("string")
            .str.strip()
            .str.lower()
        )

    # --------------------------------------------------------
    # Acquisition channel
    # --------------------------------------------------------

    if "acquisition_channel" in df.columns:
        df["acquisition_channel"] = (
            df["acquisition_channel"]
            .astype("string")
            .str.strip()
            .str.lower()
        )

    # --------------------------------------------------------
    # Signup timestamp
    # --------------------------------------------------------

    if "signup_ts" not in df.columns:
        raise ValueError(
            "captains.csv must contain 'signup_ts'. "
            "Available columns: "
            f"{df.columns.tolist()}"
        )

    df["signup_ts"] = pd.to_datetime(
        df["signup_ts"],
        errors="coerce",
    )

    # Standardized field used by downstream analysis.
    df["signup_date"] = df["signup_ts"]

    # --------------------------------------------------------
    # Remove unusable captain records
    # --------------------------------------------------------

    df = df[
        df["captain_id"].notna()
        & df["signup_date"].notna()
        & (
            df["signup_date"]
            <= CUTOFF_DATE
        )
    ]

    # --------------------------------------------------------
    # Keep one captain record
    # --------------------------------------------------------

    df = df.drop_duplicates(
        subset=["captain_id"],
        keep="first",
    )

    # --------------------------------------------------------
    # Signup month
    # --------------------------------------------------------

    df["signup_month"] = (
        df["signup_date"]
        .dt.to_period("M")
        .astype(str)
    )

    return df


def clean_doc_events(df):
    """
    Clean document verification events.
    """

    df = df.copy()

    # --------------------------------------------------------
    # Captain ID
    # --------------------------------------------------------

    if "captain_id" in df.columns:
        df["captain_id"] = (
            df["captain_id"]
            .astype("string")
            .str.strip()
        )

    # --------------------------------------------------------
    # Document type
    # --------------------------------------------------------

    if "doc_type" in df.columns:
        df["doc_type"] = (
            df["doc_type"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

    # --------------------------------------------------------
    # Event type
    # --------------------------------------------------------

    if "event_type" in df.columns:
        df["event_type"] = (
            df["event_type"]
            .astype("string")
            .str.strip()
            .str.lower()
        )

    # --------------------------------------------------------
    # Attempt number
    # --------------------------------------------------------

    if "attempt_no" in df.columns:
        df["attempt_no"] = pd.to_numeric(
            df["attempt_no"],
            errors="coerce",
        )

    required_columns = [
        "captain_id",
        "doc_type",
        "event_type",
        "attempt_no",
    ]

    available_required = [
        column
        for column in required_columns
        if column in df.columns
    ]

    if available_required:
        df = df.dropna(
            subset=available_required
        )

    if "attempt_no" in df.columns:
        df = df[
            df["attempt_no"] >= 1
        ]

    return df


def clean_approvals(df):
    """
    Clean captain approval records.
    """

    df = df.copy()

    # --------------------------------------------------------
    # Captain ID
    # --------------------------------------------------------

    if "captain_id" in df.columns:
        df["captain_id"] = (
            df["captain_id"]
            .astype("string")
            .str.strip()
        )

    # --------------------------------------------------------
    # Approval status
    # --------------------------------------------------------

    if "status" in df.columns:
        df["status"] = (
            df["status"]
            .astype("string")
            .str.strip()
            .str.lower()
        )

    # --------------------------------------------------------
    # One approval record per captain
    # --------------------------------------------------------

    if "captain_id" in df.columns:
        df = df.drop_duplicates(
            subset=["captain_id"],
            keep="last",
        )

    return df


def clean_activation(df):
    """
    Clean captain activation / first-order data.
    """

    df = df.copy()

    # --------------------------------------------------------
    # Captain ID
    # --------------------------------------------------------

    if "captain_id" in df.columns:
        df["captain_id"] = (
            df["captain_id"]
            .astype("string")
            .str.strip()
        )

        df = df.drop_duplicates(
            subset=["captain_id"],
            keep="last",
        )

    return df


def clean_airport_hourly(df):
    """
    Clean hourly airport supply-demand data.
    """

    df = df.copy()

    numeric_columns = [
        "hour",
        "requests",
        "fulfilled",
        "unfulfilled",
        "online_captains",
    ]

    # --------------------------------------------------------
    # Numeric conversion
    # --------------------------------------------------------

    for column in numeric_columns:

        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    required_columns = [
        "hour",
        "requests",
        "fulfilled",
        "unfulfilled",
        "online_captains",
    ]

    available_required = [
        column
        for column in required_columns
        if column in df.columns
    ]

    if available_required:
        df = df.dropna(
            subset=available_required
        )

    # --------------------------------------------------------
    # Valid hour
    # --------------------------------------------------------

    if "hour" in df.columns:
        df = df[
            (df["hour"] >= 0)
            & (df["hour"] <= 23)
        ]

    # --------------------------------------------------------
    # Non-negative operational metrics
    # --------------------------------------------------------

    for column in [
        "requests",
        "fulfilled",
        "unfulfilled",
        "online_captains",
    ]:

        if column in df.columns:
            df = df[
                df[column] >= 0
            ]

    return df


def save_clean_data(
    captains,
    doc_events,
    approvals,
    activation,
    airport_hourly,
    output_dir="data/processed",
):
    """
    Save cleaned datasets to the processed-data directory.
    """

    output = Path(
        output_dir
    )

    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    captains.to_csv(
        output / "captains_clean.csv",
        index=False,
    )

    doc_events.to_csv(
        output / "doc_events_clean.csv",
        index=False,
    )

    approvals.to_csv(
        output / "approvals_clean.csv",
        index=False,
    )

    activation.to_csv(
        output / "activation_clean.csv",
        index=False,
    )

    airport_hourly.to_csv(
        output / "airport_hourly_clean.csv",
        index=False,
    )
    