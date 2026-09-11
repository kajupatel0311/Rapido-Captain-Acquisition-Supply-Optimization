import pandas as pd
import numpy as np


def prepare_airport_hourly(airport_hourly):
    df = airport_hourly.copy()

    df["hour_ts"] = pd.to_datetime(
        df["hour_ts"],
        errors="coerce",
    )

    numeric_columns = [
        "requests",
        "fulfilled_requests",
        "unfulfilled_requests",
        "online_captains",
        "avg_eta_min",
        "avg_surge_multiplier",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    df["fulfilment_rate"] = (
        df["fulfilled_requests"]
        / df["requests"].replace(0, np.nan)
    )

    df["unfulfilled_rate"] = (
        df["unfulfilled_requests"]
        / df["requests"].replace(0, np.nan)
    )

    df["requests_per_online_captain"] = (
        df["requests"]
        / df["online_captains"].replace(0, np.nan)
    )

    df["hour"] = df["hour_ts"].dt.hour
    df["day_of_week"] = df["hour_ts"].dt.day_name()

    return df


def identify_airport_zones(airport_hourly):
    zone_types = (
        airport_hourly["zone_type"]
        .dropna()
        .astype(str)
        .unique()
    )

    airport_zone_types = [
        value
        for value in zone_types
        if "airport" in value.lower()
        or "terminal" in value.lower()
    ]

    return airport_zone_types


def airport_hourly_summary(
    airport_hourly,
    airport_zone_types=None,
):
    df = prepare_airport_hourly(
        airport_hourly
    )

    if airport_zone_types:
        df = df[
            df["zone_type"].isin(
                airport_zone_types
            )
        ].copy()

    summary = (
        df.groupby("hour")
        .agg(
            requests=("requests", "sum"),
            fulfilled_requests=(
                "fulfilled_requests",
                "sum",
            ),
            unfulfilled_requests=(
                "unfulfilled_requests",
                "sum",
            ),
            online_captains=(
                "online_captains",
                "mean",
            ),
            avg_eta_min=(
                "avg_eta_min",
                "mean",
            ),
        )
        .reset_index()
    )

    summary["fulfilment_rate"] = (
        summary["fulfilled_requests"]
        / summary["requests"]
    )

    summary["requests_per_online_captain"] = (
        summary["requests"]
        / summary["online_captains"].replace(
            0, np.nan
        )
    )

    return summary


def airport_zone_summary(airport_hourly):
    df = prepare_airport_hourly(
        airport_hourly
    )

    return (
        df.groupby(
            ["zone_id", "zone_type"],
            dropna=False,
        )
        .agg(
            requests=("requests", "sum"),
            fulfilled_requests=(
                "fulfilled_requests",
                "sum",
            ),
            unfulfilled_requests=(
                "unfulfilled_requests",
                "sum",
            ),
            avg_eta_min=(
                "avg_eta_min",
                "mean",
            ),
            avg_online_captains=(
                "online_captains",
                "mean",
            ),
        )
        .reset_index()
    )


def prepare_airport_trips(airport_trips):
    df = airport_trips.copy()

    df["request_ts"] = pd.to_datetime(
        df["request_ts"],
        errors="coerce",
    )

    numeric_columns = [
        "trip_distance_km",
        "fare_inr",
        "captain_cancelled",
        "got_return_fare_within_20min",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    df["hour"] = df["request_ts"].dt.hour
    df["day_of_week"] = (
        df["request_ts"].dt.day_name()
    )

    return df


def airport_trip_diagnosis(
    airport_trips,
    airport_zone_types=None,
):
    df = prepare_airport_trips(
        airport_trips
    )

    pickup_airport = pd.Series(
        False,
        index=df.index,
    )

    if "pickup_zone_type" in df.columns:
        pickup_airport = (
            df["pickup_zone_type"]
            .astype(str)
            .str.lower()
            .str.contains(
                "airport|terminal",
                regex=True,
            )
        )

    if "pickup_zone_id" in df.columns:
        airport_id_hint = (
            df["pickup_zone_id"]
            .astype(str)
            .str.lower()
            .str.contains(
                "airport|terminal",
                regex=True,
            )
        )

        pickup_airport = (
            pickup_airport
            | airport_id_hint
        )

    airport_trips_df = df[
        pickup_airport
    ].copy()

    if airport_trips_df.empty:
        return {
            "trip_count": 0,
            "summary": pd.DataFrame(),
        }

    summary = {
        "trip_count":
            len(airport_trips_df),
        "cancellation_rate":
            airport_trips_df[
                "captain_cancelled"
            ].mean(),
        "return_fare_rate":
            airport_trips_df[
                "got_return_fare_within_20min"
            ].mean(),
        "median_fare":
            airport_trips_df[
                "fare_inr"
            ].median(),
        "median_distance_km":
            airport_trips_df[
                "trip_distance_km"
            ].median(),
    }

    destination_summary = (
        airport_trips_df
        .groupby("drop_zone_type")
        .agg(
            trips=("trip_id", "count"),
            cancellation_rate=(
                "captain_cancelled",
                "mean",
            ),
            return_fare_rate=(
                "got_return_fare_within_20min",
                "mean",
            ),
            median_fare=(
                "fare_inr",
                "median",
            ),
            median_distance_km=(
                "trip_distance_km",
                "median",
            ),
        )
        .reset_index()
        .sort_values(
            "trips",
            ascending=False,
        )
    )

    return {
        "trip_count":
            len(airport_trips_df),
        "summary":
            pd.DataFrame([summary]),
        "destination_summary":
            destination_summary,
    }
