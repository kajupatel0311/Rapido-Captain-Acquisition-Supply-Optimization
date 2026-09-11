import pandas as pd
import numpy as np


SEGMENT_COLUMNS = [
    "city",
    "vehicle_type",
    "acquisition_channel",
    "device_tier",
    "app_language",
    "age_band",
]


def calculate_failure_reasons(doc_events):
    failures = doc_events[
        doc_events["event_type"]
        == "verification_fail"
    ].copy()

    if failures.empty:
        return pd.DataFrame()

    result = (
        failures
        .groupby(
            ["doc_type", "failure_reason"],
            dropna=False,
        )
        .agg(
            failures=("captain_id", "count"),
            affected_captains=("captain_id", "nunique"),
        )
        .reset_index()
        .sort_values(
            "affected_captains",
            ascending=False,
        )
    )

    return result


def calculate_document_dropoff(
    funnel,
    document_state,
):
    rows = []

    for doc_type, group in document_state.groupby(
        "doc_type"
    ):
        required = group["captain_id"].nunique()

        cleared = int(group["cleared"].sum())

        rows.append(
            {
                "doc_type": doc_type,
                "required_captains": required,
                "cleared_captains": cleared,
                "not_cleared": required - cleared,
                "clearance_rate": (
                    cleared / required
                    if required
                    else np.nan
                ),
            }
        )

    return pd.DataFrame(rows).sort_values(
        "not_cleared",
        ascending=False,
    )


def segment_document_leak(
    funnel,
    document_state,
    doc_type,
    segment_columns=None,
):
    if segment_columns is None:
        segment_columns = SEGMENT_COLUMNS

    state = document_state[
        document_state["doc_type"] == doc_type
    ].copy()

    base = funnel[
        [
            "captain_id"
        ] + [
            c for c in segment_columns
            if c in funnel.columns
        ]
    ].drop_duplicates("captain_id")

    state = state.merge(
        base,
        on="captain_id",
        how="left",
    )

    group_columns = [
        c for c in segment_columns
        if c in state.columns
    ]

    result = (
        state
        .groupby(group_columns, dropna=False)
        .agg(
            captains=("captain_id", "nunique"),
            cleared=("cleared", "sum"),
        )
        .reset_index()
    )

    result["not_cleared"] = (
        result["captains"]
        - result["cleared"]
    )

    result["clearance_rate"] = (
        result["cleared"]
        / result["captains"]
    )

    return result.sort_values(
        "not_cleared",
        ascending=False,
    )


def estimate_recoverable_captains(
    segment_result,
    benchmark_rate,
    realization_factor=1.0,
):
    result = segment_result.copy()

    result["benchmark_rate"] = benchmark_rate

    result["theoretical_recovery"] = (
        result["captains"]
        * (
            benchmark_rate
            - result["clearance_rate"]
        )
    ).clip(lower=0)

    result["estimated_recovery"] = (
        result["theoretical_recovery"]
        * realization_factor
    )

    return result
