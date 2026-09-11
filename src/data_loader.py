import pandas as pd

from src.config import RAW_FILES


# ============================================================
# TIMESTAMP PARSING
# ============================================================

def parse_timestamp(series):
    """
    Parse timestamps consistently.

    format='mixed' prevents pandas from repeatedly trying to
    infer different formats element by element.
    """

    return pd.to_datetime(
        series,
        errors="coerce",
        format="mixed",
    )


# ============================================================
# CSV LOADING
# ============================================================

def read_csv(path):
    """
    Load a CSV file.
    """

    return pd.read_csv(
        path,
        low_memory=False,
    )


# ============================================================
# LOAD ALL DATA
# ============================================================

def load_all_data():
    """
    Load all seven raw datasets.

    Returns a dictionary with the same keys expected by
    run_analysis.py.
    """

    data = {}

    # --------------------------------------------------------
    # Captains
    # --------------------------------------------------------

    captains = read_csv(
        RAW_FILES["captains"]
    )

    if "signup_ts" in captains.columns:
        captains["signup_ts"] = parse_timestamp(
            captains["signup_ts"]
        )

    data["captains"] = captains

    # --------------------------------------------------------
    # Document events
    # --------------------------------------------------------

    doc_events = read_csv(
        RAW_FILES["doc_events"]
    )

    if "event_ts" in doc_events.columns:
        doc_events["event_ts"] = parse_timestamp(
            doc_events["event_ts"]
        )

    data["doc_events"] = doc_events

    # --------------------------------------------------------
    # Approvals
    # --------------------------------------------------------

    approvals = read_csv(
        RAW_FILES["approvals"]
    )

    if "decision_ts" in approvals.columns:
        approvals["decision_ts"] = parse_timestamp(
            approvals["decision_ts"]
        )

    data["approvals"] = approvals

    # --------------------------------------------------------
    # Activation
    # --------------------------------------------------------

    activation = read_csv(
        RAW_FILES["activation"]
    )

    if "first_order_ts" in activation.columns:
        activation["first_order_ts"] = parse_timestamp(
            activation["first_order_ts"]
        )

    data["activation"] = activation

    # --------------------------------------------------------
    # Nudges
    # --------------------------------------------------------

    nudges = read_csv(
        RAW_FILES["nudges"]
    )

    if "sent_ts" in nudges.columns:
        nudges["sent_ts"] = parse_timestamp(
            nudges["sent_ts"]
        )

    data["nudges"] = nudges

    # --------------------------------------------------------
    # Airport hourly
    # --------------------------------------------------------

    airport_hourly = read_csv(
        RAW_FILES["airport_hourly"]
    )

    if "hour_ts" in airport_hourly.columns:
        airport_hourly["hour_ts"] = parse_timestamp(
            airport_hourly["hour_ts"]
        )

    data["airport_hourly"] = airport_hourly

    # --------------------------------------------------------
    # Airport trips
    # --------------------------------------------------------

    airport_trips = read_csv(
        RAW_FILES["airport_trips"]
    )

    if "request_ts" in airport_trips.columns:
        airport_trips["request_ts"] = parse_timestamp(
            airport_trips["request_ts"]
        )

    data["airport_trips"] = airport_trips

    return data
