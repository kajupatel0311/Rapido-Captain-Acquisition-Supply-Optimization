from __future__ import annotations

import json
from typing import Optional

import numpy as np
import pandas as pd


# ============================================================
# GENERAL HELPERS
# ============================================================

def _safe_divide(numerator, denominator):
    """
    Safely divide two values/Series.

    Zero denominators are converted to NaN.
    """
    numerator = pd.to_numeric(
        numerator,
        errors="coerce",
    )

    denominator = pd.to_numeric(
        denominator,
        errors="coerce",
    )

    return numerator / denominator.replace(
        0,
        np.nan,
    )


def _normalise_doc_type(value) -> str:
    """
    Normalize document names to the canonical names
    used in the assignment.
    """

    if pd.isna(value):
        return ""

    value = str(value).strip().upper()

    mapping = {
        "DL": "DL",
        "DRIVING_LICENCE": "DL",
        "DRIVING_LICENSE": "DL",
        "DRIVING LICENCE": "DL",
        "DRIVING LICENSE": "DL",

        "RC": "RC",
        "REGISTRATION_CERTIFICATE": "RC",
        "REGISTRATION CERTIFICATE": "RC",

        "AADHAAR": "AADHAAR",
        "AADHAR": "AADHAAR",

        "PERMIT": "PERMIT",

        "FITNESS": "FITNESS",
        "FITNESS_CERTIFICATE": "FITNESS",
        "FITNESS CERTIFICATE": "FITNESS",

        "INSURANCE": "INSURANCE",
    }

    return mapping.get(
        value,
        value,
    )


# ============================================================
# DOCUMENT STATUS
# ============================================================

def _build_document_status(
    doc_events: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the latest verification status for every
    captain-document combination.

    A document is considered cleared when its latest
    verification event is verification_pass.
    """

    if doc_events.empty:
        return pd.DataFrame(
            columns=[
                "captain_id",
                "doc_type",
                "document_passed",
                "document_failed",
            ]
        )

    required_columns = {
        "captain_id",
        "doc_type",
        "event_type",
    }

    missing = (
        required_columns
        - set(doc_events.columns)
    )

    if missing:
        raise ValueError(
            "doc_events is missing required columns: "
            + ", ".join(sorted(missing))
        )

    df = doc_events.copy()

    df["doc_type"] = (
        df["doc_type"]
        .map(_normalise_doc_type)
    )

    if "event_ts" in df.columns:
        df["event_ts"] = pd.to_datetime(
            df["event_ts"],
            errors="coerce",
        )
    else:
        df["event_ts"] = pd.NaT

    if "attempt_no" in df.columns:
        df["attempt_no"] = pd.to_numeric(
            df["attempt_no"],
            errors="coerce",
        ).fillna(0)
    else:
        df["attempt_no"] = 0

    event_order = {
        "upload_success": 1,
        "verification_fail": 2,
        "verification_pass": 3,
    }

    df["_event_order"] = (
        df["event_type"]
        .astype(str)
        .str.lower()
        .map(event_order)
        .fillna(0)
    )

    df = df.sort_values(
        [
            "captain_id",
            "doc_type",
            "event_ts",
            "attempt_no",
            "_event_order",
        ]
    )

    latest = (
        df.groupby(
            [
                "captain_id",
                "doc_type",
            ],
            as_index=False,
        )
        .tail(1)
        .copy()
    )

    latest["document_passed"] = (
        latest["event_type"]
        .astype(str)
        .str.lower()
        .eq("verification_pass")
    )

    latest["document_failed"] = (
        latest["event_type"]
        .astype(str)
        .str.lower()
        .eq("verification_fail")
    )

    return latest[
        [
            "captain_id",
            "doc_type",
            "document_passed",
            "document_failed",
        ]
    ].reset_index(drop=True)


# ============================================================
# A2 - BUILD STAGE SEGMENT TABLE
# ============================================================

def build_stage_segment_table(
    captains: pd.DataFrame,
    doc_events: pd.DataFrame,
    approvals: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build captain-level sequential onboarding stage data.

    Required sequence:

        DL
        RC
        AADHAAR
        PERMIT       -> Auto/Cab only
        FITNESS
        INSURANCE
        APPROVED

    ERickshaw skips Permit.
    """

    if captains.empty:
        return pd.DataFrame()

    if "captain_id" not in captains.columns:
        raise ValueError(
            "captains must contain captain_id."
        )

    base_columns = [
        "captain_id",
        "city",
        "vehicle_type",
        "acquisition_channel",
        "signup_zone_id",
        "device_tier",
        "app_language",
        "age_band",
        "signup_ts",
    ]

    available_columns = [
        column
        for column in base_columns
        if column in captains.columns
    ]

    base = captains[
        available_columns
    ].copy()

    default_columns = {
        "city": "Unknown",
        "vehicle_type": "Unknown",
        "acquisition_channel": "Unknown",
        "signup_zone_id": "Unknown",
        "device_tier": "Unknown",
        "app_language": "Unknown",
        "age_band": "Unknown",
    }

    for column, default_value in default_columns.items():
        if column not in base.columns:
            base[column] = default_value

    if "signup_ts" in base.columns:
        base["signup_ts"] = pd.to_datetime(
            base["signup_ts"],
            errors="coerce",
        )
    else:
        base["signup_ts"] = pd.NaT

    # --------------------------------------------------------
    # Document status
    # --------------------------------------------------------

    document_status = _build_document_status(
        doc_events
    )

    if document_status.empty:
        status_pivot = pd.DataFrame(
            columns=[
                "captain_id",
                "DL",
                "RC",
                "AADHAAR",
                "PERMIT",
                "FITNESS",
                "INSURANCE",
            ]
        )

    else:
        status_pivot = (
            document_status[
                [
                    "captain_id",
                    "doc_type",
                    "document_passed",
                ]
            ]
            .pivot_table(
                index="captain_id",
                columns="doc_type",
                values="document_passed",
                aggfunc="max",
                fill_value=False,
            )
            .reset_index()
        )

    for document in [
        "DL",
        "RC",
        "AADHAAR",
        "PERMIT",
        "FITNESS",
        "INSURANCE",
    ]:
        if document not in status_pivot.columns:
            status_pivot[document] = False

    base = base.merge(
        status_pivot[
            [
                "captain_id",
                "DL",
                "RC",
                "AADHAAR",
                "PERMIT",
                "FITNESS",
                "INSURANCE",
            ]
        ],
        on="captain_id",
        how="left",
    )

    # Fix FutureWarning:
    # convert to boolean explicitly instead of relying on
    # object dtype fillna downcasting.
    for column in [
        "DL",
        "RC",
        "AADHAAR",
        "PERMIT",
        "FITNESS",
        "INSURANCE",
    ]:
        base[column] = (
            base[column]
            .astype("boolean")
            .fillna(False)
            .astype(bool)
        )

    # --------------------------------------------------------
    # Vehicle-specific Permit requirement
    # --------------------------------------------------------

    base["permit_required"] = (
        base["vehicle_type"]
        .astype(str)
        .str.strip()
        .str.upper()
        .isin(
            [
                "AUTO",
                "CAB",
            ]
        )
    )

    # --------------------------------------------------------
    # Sequential stages
    # --------------------------------------------------------

    base["stage_DL"] = (
        base["DL"]
    )

    base["stage_RC"] = (
        base["stage_DL"]
        & base["RC"]
    )

    base["stage_AADHAAR"] = (
        base["stage_RC"]
        & base["AADHAAR"]
    )

    base["stage_PERMIT"] = np.where(
        base["permit_required"],
        (
            base["stage_AADHAAR"]
            & base["PERMIT"]
        ),
        base["stage_AADHAAR"],
    )

    base["stage_FITNESS"] = (
        base["stage_PERMIT"]
        & base["FITNESS"]
    )

    base["stage_INSURANCE"] = (
        base["stage_FITNESS"]
        & base["INSURANCE"]
    )

    base["all_documents_cleared"] = (
        base["stage_INSURANCE"]
    )

    # --------------------------------------------------------
    # Approval data
    # --------------------------------------------------------

    if not approvals.empty:

        approval_columns = [
            "captain_id",
            "decision_ts",
            "final_status",
            "last_stage_reached",
            "docs_cleared",
        ]

        available_approval_columns = [
            column
            for column in approval_columns
            if column in approvals.columns
        ]

        approval_df = approvals[
            available_approval_columns
        ].copy()

        if "decision_ts" in approval_df.columns:
            approval_df["decision_ts"] = (
                pd.to_datetime(
                    approval_df["decision_ts"],
                    errors="coerce",
                )
            )

        base = base.merge(
            approval_df,
            on="captain_id",
            how="left",
            suffixes=(
                "",
                "_approval",
            ),
        )

    if "final_status" not in base.columns:
        base["final_status"] = "unknown"

    base["approved"] = (
        base["final_status"]
        .astype(str)
        .str.lower()
        .eq("approved")
    )

    # --------------------------------------------------------
    # Calculated stage reached
    # --------------------------------------------------------

    def calculate_stage(row):

        if not row["stage_DL"]:
            return "DL"

        if not row["stage_RC"]:
            return "RC"

        if not row["stage_AADHAAR"]:
            return "AADHAAR"

        if (
            row["permit_required"]
            and not row["stage_PERMIT"]
        ):
            return "PERMIT"

        if not row["stage_FITNESS"]:
            return "FITNESS"

        if not row["stage_INSURANCE"]:
            return "INSURANCE"

        if row["approved"]:
            return "APPROVED"

        return "ALL_DOCUMENTS_CLEARED"

    base["calculated_stage_reached"] = (
        base.apply(
            calculate_stage,
            axis=1,
        )
    )

    # --------------------------------------------------------
    # Signup month
    # --------------------------------------------------------

    base["signup_month"] = (
        base["signup_ts"]
        .dt.to_period("M")
        .astype(str)
    )

    return base


# ============================================================
# A2 - SEGMENT LEAK SUMMARY
# ============================================================

def summarize_segment_leaks(
    stage_segment_table: pd.DataFrame,
) -> pd.DataFrame:
    """
    Summarise sequential leaks by:

        city
        vehicle_type
        acquisition_channel
        stage
    """

    if stage_segment_table.empty:
        return pd.DataFrame()

    df = stage_segment_table.copy()

    segment_columns = [
        "city",
        "vehicle_type",
        "acquisition_channel",
    ]

    for column in segment_columns:
        if column not in df.columns:
            df[column] = "Unknown"

    stage_definitions = [
        (
            "DL",
            "stage_DL",
            None,
        ),
        (
            "RC",
            "stage_RC",
            "stage_DL",
        ),
        (
            "AADHAAR",
            "stage_AADHAAR",
            "stage_RC",
        ),
        (
            "PERMIT",
            "stage_PERMIT",
            "permit_required",
        ),
        (
            "FITNESS",
            "stage_FITNESS",
            "stage_PERMIT",
        ),
        (
            "INSURANCE",
            "stage_INSURANCE",
            "stage_FITNESS",
        ),
    ]

    results = []

    for (
        stage_name,
        cleared_column,
        reached_rule,
    ) in stage_definitions:

        working = df.copy()

        if reached_rule is None:

            working["_reached"] = True

        elif reached_rule == "permit_required":

            working["_reached"] = (
                working[
                    "permit_required"
                ]
                .astype(bool)
            )

        else:

            working["_reached"] = (
                working[
                    reached_rule
                ]
                .astype(bool)
            )

        working["_cleared"] = (
            working[
                cleared_column
            ]
            .astype(bool)
        )

        working = working[
            working["_reached"]
        ].copy()

        if working.empty:
            continue

        grouped = (
            working
            .groupby(
                segment_columns
            )
            .agg(
                reached=(
                    "captain_id",
                    "nunique",
                ),
                cleared=(
                    "_cleared",
                    "sum",
                ),
            )
            .reset_index()
        )

        grouped["not_cleared"] = (
            grouped["reached"]
            - grouped["cleared"]
        )

        grouped["stage_conversion"] = (
            _safe_divide(
                grouped["cleared"],
                grouped["reached"],
            )
        )

        grouped["stage_dropoff"] = (
            1
            - grouped["stage_conversion"]
        )

        grouped["stage"] = stage_name

        results.append(
            grouped
        )

    if not results:
        return pd.DataFrame()

    result = pd.concat(
        results,
        ignore_index=True,
    )

    return result[
        [
            "city",
            "vehicle_type",
            "acquisition_channel",
            "stage",
            "reached",
            "cleared",
            "not_cleared",
            "stage_conversion",
            "stage_dropoff",
        ]
    ].sort_values(
        "not_cleared",
        ascending=False,
    ).reset_index(
        drop=True
    )


# ============================================================
# A2 - ACTIONABLE SEGMENTS
# ============================================================

def identify_actionable_segments(
    segment_leaks: pd.DataFrame,
    minimum_reached: int = 100,
) -> pd.DataFrame:
    """
    Rank segment-stage leaks.

    Actionability score:

        not_cleared × stage_dropoff

    This is a prioritisation metric, not a causal estimate.
    """

    if segment_leaks.empty:
        return pd.DataFrame()

    df = segment_leaks.copy()

    df = df[
        df["reached"]
        >= minimum_reached
    ].copy()

    if df.empty:
        return df

    df["actionability_score"] = (
        df["not_cleared"]
        * df["stage_dropoff"]
    )

    df["actionability_score"] = (
        df["actionability_score"]
        .replace(
            [
                np.inf,
                -np.inf,
            ],
            np.nan,
        )
        .fillna(0)
    )

    return df.sort_values(
        [
            "actionability_score",
            "not_cleared",
        ],
        ascending=False,
    ).reset_index(
        drop=True
    )


# ============================================================
# A2 - INCREMENTAL APPROVAL ESTIMATION
# ============================================================

def estimate_incremental_approvals(
    actionable_segments: pd.DataFrame,
    approvals: Optional[pd.DataFrame] = None,
    improvement_rate: float = 0.20,
    relative_failure_reduction: Optional[float] = None,
    minimum_reached: int = 100,
    stage_segment_table: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Estimate incremental approvals from fixing part of a stage leak.

    Preferred calculation
    ---------------------
    When stage_segment_table is supplied, this function produces a
    genuinely monthly opportunity estimate:

        monthly failed captains
        × recovery assumption
        × downstream approval probability

    The downstream approval probability is estimated from mature signup
    cohorts for the same city / vehicle / acquisition-channel / stage.

    Cohort rule
    -----------
    The latest signup month in the data is treated as immature and is
    excluded from opportunity sizing. This is appropriate for this
    dataset because the extraction date is 2026-06-30 and the latest
    signup cohort is therefore incomplete.

    This remains a scenario estimate, not a causal forecast.
    """

    if relative_failure_reduction is not None:
        improvement_rate = relative_failure_reduction

    if not 0 <= improvement_rate <= 1:
        raise ValueError(
            "improvement_rate must be between 0 and 1."
        )

    if actionable_segments is None or actionable_segments.empty:
        return pd.DataFrame()

    if stage_segment_table is None or stage_segment_table.empty:
        # Backward-compatible fallback. This should not be used by the
        # main pipeline because it cannot produce a true monthly estimate.
        df = actionable_segments.copy()

        if "not_cleared" not in df.columns:
            if {"reached", "cleared"}.issubset(df.columns):
                df["not_cleared"] = (
                    df["reached"] - df["cleared"]
                )
            else:
                return pd.DataFrame()

        if "reached" not in df.columns:
            df["reached"] = df["not_cleared"]

        overall_approval_rate = 0.0

        if (
            approvals is not None
            and not approvals.empty
            and "final_status" in approvals.columns
        ):
            status = (
                approvals["final_status"]
                .astype(str)
                .str.lower()
            )
            overall_approval_rate = float(
                status.eq("approved").mean()
            )

        df["downstream_approval_rate"] = (
            overall_approval_rate
        )
        df["recoverable_captains"] = (
            pd.to_numeric(
                df["not_cleared"],
                errors="coerce",
            ).fillna(0)
            * improvement_rate
        )
        df["estimated_incremental_approvals"] = (
            df["recoverable_captains"]
            * df["downstream_approval_rate"]
        )

        # Explicitly do NOT call this monthly because the source table
        # has no monthly population.
        df["monthly_incremental_approvals"] = np.nan
        df["improvement_rate"] = improvement_rate
        df["scenario_note"] = (
            "Fallback segment-level scenario. Monthly sizing requires "
            "stage_segment_table."
        )

        if minimum_reached > 0:
            df = df[
                df["reached"] >= minimum_reached
            ].copy()

        return df.sort_values(
            "estimated_incremental_approvals",
            ascending=False,
        ).reset_index(drop=True)

    # ------------------------------------------------------------
    # Prepare captain-level stage data
    # ------------------------------------------------------------

    df = stage_segment_table.copy()

    required = {
        "captain_id",
        "city",
        "vehicle_type",
        "acquisition_channel",
        "signup_month",
        "approved",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            "stage_segment_table is missing required columns: "
            + ", ".join(sorted(missing))
        )

    segment_columns = [
        "city",
        "vehicle_type",
        "acquisition_channel",
    ]

    stage_definitions = [
        ("DL", "stage_DL", None),
        ("RC", "stage_RC", "stage_DL"),
        ("AADHAAR", "stage_AADHAAR", "stage_RC"),
        ("PERMIT", "stage_PERMIT", "permit_required"),
        ("FITNESS", "stage_FITNESS", "stage_PERMIT"),
        ("INSURANCE", "stage_INSURANCE", "stage_FITNESS"),
    ]

    # Clean month values.
    df["signup_month"] = (
        df["signup_month"]
        .astype("string")
    )

    valid_months = (
        df.loc[
            df["signup_month"].notna()
            & df["signup_month"].ne("<NA>"),
            "signup_month",
        ]
        .drop_duplicates()
        .tolist()
    )

    if not valid_months:
        return pd.DataFrame()

    valid_months = sorted(valid_months)

    # Latest signup month is treated as immature.
    mature_months = valid_months[:-1]

    if not mature_months:
        return pd.DataFrame()

    df_mature = df[
        df["signup_month"].isin(mature_months)
    ].copy()

    # ------------------------------------------------------------
    # Build pooled downstream approval rates by segment + stage
    # ------------------------------------------------------------

    downstream_rows = []

    for stage_name, cleared_column, reached_rule in stage_definitions:
        working = df_mature.copy()

        if reached_rule is None:
            working["_reached"] = True

        elif reached_rule == "permit_required":
            working["_reached"] = (
                working["permit_required"]
                .astype(bool)
            )

        else:
            working["_reached"] = (
                working[reached_rule]
                .astype(bool)
            )

        working["_cleared"] = (
            working[cleared_column]
            .astype(bool)
        )

        # A captain can only be approved if the stage was cleared.
        working["_approved_after_stage"] = (
            working["_cleared"]
            & working["approved"].astype(bool)
        )

        grouped = (
            working[
                working["_reached"]
            ]
            .groupby(segment_columns)
            .agg(
                reached=(
                    "captain_id",
                    "nunique",
                ),
                cleared=(
                    "_cleared",
                    "sum",
                ),
                approved_after_stage=(
                    "_approved_after_stage",
                    "sum",
                ),
            )
            .reset_index()
        )

        grouped["downstream_approval_rate"] = (
            _safe_divide(
                grouped["approved_after_stage"],
                grouped["cleared"],
            )
            .fillna(0)
        )

        grouped["stage"] = stage_name

        downstream_rows.append(
            grouped[
                segment_columns
                + [
                    "stage",
                    "downstream_approval_rate",
                ]
            ]
        )

    downstream = pd.concat(
        downstream_rows,
        ignore_index=True,
    )

    # ------------------------------------------------------------
    # Identify actionable segment/stage combinations
    # ------------------------------------------------------------

    action = actionable_segments.copy()

    if "stage" not in action.columns:
        return pd.DataFrame()

    action = action[
        segment_columns
        + ["stage"]
    ].drop_duplicates()

    # Only size actionable rows that meet the minimum historical
    # population threshold in mature cohorts.
    mature_action = (
        downstream.merge(
            action,
            on=segment_columns + ["stage"],
            how="inner",
        )
    )

    if mature_action.empty:
        return pd.DataFrame()

    # ------------------------------------------------------------
    # Calculate monthly failed populations
    # ------------------------------------------------------------

    monthly_rows = []

    for stage_name, cleared_column, reached_rule in stage_definitions:
        working = df_mature.copy()

        if reached_rule is None:
            working["_reached"] = True

        elif reached_rule == "permit_required":
            working["_reached"] = (
                working["permit_required"]
                .astype(bool)
            )

        else:
            working["_reached"] = (
                working[reached_rule]
                .astype(bool)
            )

        working["_cleared"] = (
            working[cleared_column]
            .astype(bool)
        )

        monthly = (
            working[
                working["_reached"]
            ]
            .groupby(
                [
                    "signup_month",
                    *segment_columns,
                ]
            )
            .agg(
                reached=(
                    "captain_id",
                    "nunique",
                ),
                cleared=(
                    "_cleared",
                    "sum",
                ),
            )
            .reset_index()
        )

        monthly["not_cleared"] = (
            monthly["reached"]
            - monthly["cleared"]
        )

        monthly["stage"] = stage_name

        monthly_rows.append(monthly)

    monthly = pd.concat(
        monthly_rows,
        ignore_index=True,
    )

    # Restrict to the actionable segment/stage combinations.
    monthly = monthly.merge(
        action,
        on=segment_columns + ["stage"],
        how="inner",
    )

    monthly = monthly.merge(
        downstream,
        on=segment_columns + ["stage"],
        how="left",
    )

    if monthly.empty:
        return monthly

    # ------------------------------------------------------------
    # Scenario calculation
    # ------------------------------------------------------------

    monthly["recoverable_captains"] = (
        monthly["not_cleared"]
        * improvement_rate
    )

    monthly["estimated_incremental_approvals"] = (
        monthly["recoverable_captains"]
        * monthly["downstream_approval_rate"]
    )

    # This is now genuinely monthly because every row is a signup cohort.
    monthly["monthly_incremental_approvals"] = (
        monthly["estimated_incremental_approvals"]
    )

    monthly["improvement_rate"] = improvement_rate

    monthly["scenario_note"] = (
        "Scenario estimate for mature signup cohorts only. "
        f"Assumes {improvement_rate:.0%} relative reduction in "
        "stage non-clearance. Downstream approval rate is pooled "
        "within city × vehicle × acquisition channel × stage. "
        "Not causal."
    )

    monthly["maturity_rule"] = (
        "Latest signup month excluded as immature."
    )

    if minimum_reached > 0:
        monthly = monthly[
            monthly["reached"] >= minimum_reached
        ].copy()

    # Useful ordering for the output.
    return monthly.sort_values(
        [
            "monthly_incremental_approvals",
            "signup_month",
        ],
        ascending=[
            False,
            True,
        ],
    ).reset_index(drop=True)


# ============================================================
# A3 - CAMPAIGN ANALYSIS
# ============================================================

def campaign_confidence_analysis(
    captains: pd.DataFrame,
    approvals: pd.DataFrame,
    nudges: pd.DataFrame,
    campaign_id: str = "CAMP_WA_002",
) -> dict:
    """
    Evaluate campaign association with approval.

    The analysis reports:

        observed approval rates
        observed lift
        95% confidence interval
        adjusted logistic-regression estimate
        odds ratio

    IMPORTANT:
    Because the campaign is not confirmed randomized,
    the result is observational association, not causal impact.
    """

    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    if captains.empty:
        return {
            "campaign_id": campaign_id,
            "treated_captains": 0,
            "control_captains": 0,
            "treated_approval_rate": None,
            "control_approval_rate": None,
            "observed_lift_pp": None,
            "observed_lift_ci_low_pp": None,
            "observed_lift_ci_high_pp": None,
            "adjusted_treated_probability": None,
            "adjusted_control_probability": None,
            "adjusted_lift_pp": None,
            "log_odds_coefficient": None,
            "odds_ratio": None,
            "odds_ratio_ci_low": None,
            "odds_ratio_ci_high": None,
            "p_value": None,
            "model_observations": 0,
            "interpretation": (
                "No captain data available."
            ),
        }

    base = captains.copy()

    # --------------------------------------------------------
    # Approval outcome
    # --------------------------------------------------------

    if approvals.empty:
        base["approved"] = 0

    else:

        approval_df = approvals[
            [
                "captain_id",
                "final_status",
            ]
        ].copy()

        approval_df["approved"] = (
            approval_df[
                "final_status"
            ]
            .astype(str)
            .str.lower()
            .eq("approved")
            .astype(int)
        )

        base = base.merge(
            approval_df[
                [
                    "captain_id",
                    "approved",
                ]
            ],
            on="captain_id",
            how="left",
        )

        base["approved"] = (
            base["approved"]
            .fillna(0)
            .astype(int)
        )

    # --------------------------------------------------------
    # Campaign treatment
    # --------------------------------------------------------

    campaign_nudges = nudges[
        nudges[
            "campaign_id"
        ]
        .astype(str)
        .eq(str(campaign_id))
    ].copy()

    if campaign_nudges.empty:

        return {
            "campaign_id": campaign_id,
            "treated_captains": 0,
            "control_captains": int(
                len(base)
            ),
            "treated_approval_rate": None,
            "control_approval_rate": float(
                base["approved"].mean()
            ),
            "observed_lift_pp": None,
            "observed_lift_ci_low_pp": None,
            "observed_lift_ci_high_pp": None,
            "adjusted_treated_probability": None,
            "adjusted_control_probability": None,
            "adjusted_lift_pp": None,
            "log_odds_coefficient": None,
            "odds_ratio": None,
            "odds_ratio_ci_low": None,
            "odds_ratio_ci_high": None,
            "p_value": None,
            "model_observations": int(
                len(base)
            ),
            "interpretation": (
                "Campaign not found in nudges."
            ),
        }

    treated_ids = set(
        campaign_nudges[
            "captain_id"
        ].dropna()
    )

    base["treated"] = (
        base["captain_id"]
        .isin(treated_ids)
        .astype(int)
    )

    # --------------------------------------------------------
    # Descriptive result
    # --------------------------------------------------------

    treated = base[
        base["treated"] == 1
    ]

    control = base[
        base["treated"] == 0
    ]

    treated_n = len(treated)
    control_n = len(control)

    treated_rate = (
        treated["approved"].mean()
        if treated_n > 0
        else np.nan
    )

    control_rate = (
        control["approved"].mean()
        if control_n > 0
        else np.nan
    )

    observed_lift = (
        treated_rate
        - control_rate
    )

    # --------------------------------------------------------
    # Confidence interval
    # --------------------------------------------------------

    ci_low = np.nan
    ci_high = np.nan

    try:

        from statsmodels.stats.proportion import (
            confint_proportions_2indep,
        )

        ci_low, ci_high = (
            confint_proportions_2indep(
                count1=int(
                    treated[
                        "approved"
                    ].sum()
                ),
                nobs1=treated_n,
                count2=int(
                    control[
                        "approved"
                    ].sum()
                ),
                nobs2=control_n,
                method="wald",
                compare="diff",
                alpha=0.05,
            )
        )

    except Exception:

        if (
            treated_n > 0
            and control_n > 0
        ):

            se = np.sqrt(
                (
                    treated_rate
                    * (
                        1
                        - treated_rate
                    )
                    / treated_n
                )
                +
                (
                    control_rate
                    * (
                        1
                        - control_rate
                    )
                    / control_n
                )
            )

            ci_low = (
                observed_lift
                - 1.96 * se
            )

            ci_high = (
                observed_lift
                + 1.96 * se
            )

    # --------------------------------------------------------
    # Adjusted model
    # --------------------------------------------------------

    model_features = [
        "city",
        "vehicle_type",
        "acquisition_channel",
        "device_tier",
        "app_language",
        "age_band",
    ]

    model_features = [
        column
        for column in model_features
        if column in base.columns
    ]

    if "signup_ts" in base.columns:

        base["signup_ts"] = pd.to_datetime(
            base["signup_ts"],
            errors="coerce",
        )

        base["signup_month"] = (
            base["signup_ts"]
            .dt.to_period("M")
            .astype(str)
        )

        model_features.append(
            "signup_month"
        )

    adjusted_treated_probability = np.nan
    adjusted_control_probability = np.nan
    adjusted_lift = np.nan

    coefficient = np.nan
    odds_ratio = np.nan
    odds_ratio_ci_low = np.nan
    odds_ratio_ci_high = np.nan
    p_value = np.nan

    if (
        model_features
        and base["treated"].nunique() > 1
        and base["approved"].nunique() > 1
    ):

        X = base[
            model_features
            + ["treated"]
        ].copy()

        y = base[
            "approved"
        ]

        categorical_features = [
            column
            for column in X.columns
            if X[column].dtype == "object"
            or str(
                X[column].dtype
            ).startswith(
                "category"
            )
        ]

        numeric_features = [
            column
            for column in X.columns
            if column
            not in categorical_features
        ]

        transformers = []

        if categorical_features:

            transformers.append(
                (
                    "categorical",
                    Pipeline(
                        steps=[
                            (
                                "imputer",
                                SimpleImputer(
                                    strategy=(
                                        "most_frequent"
                                    )
                                ),
                            ),
                            (
                                "onehot",
                                OneHotEncoder(
                                    handle_unknown=(
                                        "ignore"
                                    )
                                ),
                            ),
                        ]
                    ),
                    categorical_features,
                )
            )

        if numeric_features:

            transformers.append(
                (
                    "numeric",
                    Pipeline(
                        steps=[
                            (
                                "imputer",
                                SimpleImputer(
                                    strategy="median"
                                ),
                            )
                        ]
                    ),
                    numeric_features,
                )
            )

        preprocessor = (
            ColumnTransformer(
                transformers=transformers
            )
        )

        model = LogisticRegression(
            max_iter=1000,
            solver="liblinear",
        )

        pipeline = Pipeline(
            steps=[
                (
                    "preprocessor",
                    preprocessor,
                ),
                (
                    "model",
                    model,
                ),
            ]
        )

        try:

            pipeline.fit(
                X,
                y,
            )

            treated_prediction = X.copy()
            control_prediction = X.copy()

            treated_prediction[
                "treated"
            ] = 1

            control_prediction[
                "treated"
            ] = 0

            adjusted_treated_probability = (
                pipeline
                .predict_proba(
                    treated_prediction
                )[:, 1]
                .mean()
            )

            adjusted_control_probability = (
                pipeline
                .predict_proba(
                    control_prediction
                )[:, 1]
                .mean()
            )

            adjusted_lift = (
                adjusted_treated_probability
                - adjusted_control_probability
            )

            # ------------------------------------------------
            # Treatment coefficient
            # ------------------------------------------------

            fitted_model = (
                pipeline
                .named_steps["model"]
            )

            transformed_names = (
                pipeline
                .named_steps[
                    "preprocessor"
                ]
                .get_feature_names_out()
            )

            treatment_index = None

            for index, name in enumerate(
                transformed_names
            ):

                if name.endswith(
                    "__treated"
                ):

                    treatment_index = (
                        index
                    )
                    break

            if treatment_index is not None:

                coefficient = float(
                    fitted_model.coef_[0][
                        treatment_index
                    ]
                )

                odds_ratio = float(
                    np.exp(
                        coefficient
                    )
                )

            # ------------------------------------------------
            # Statsmodels CI / p-value
            # ------------------------------------------------

            try:

                import statsmodels.api as sm

                transformed_X = (
                    pipeline
                    .named_steps[
                        "preprocessor"
                    ]
                    .transform(X)
                )

                if hasattr(
                    transformed_X,
                    "toarray",
                ):
                    transformed_X = (
                        transformed_X
                        .toarray()
                    )

                transformed_X = (
                    np.asarray(
                        transformed_X
                    )
                )

                transformed_X = (
                    sm.add_constant(
                        transformed_X,
                        has_constant="add",
                    )
                )

                sm_model = (
                    sm.Logit(
                        y,
                        transformed_X,
                    )
                    .fit(
                        disp=False
                    )
                )

                sm_names = (
                    ["const"]
                    + list(
                        transformed_names
                    )
                )

                sm_treatment_index = None

                for index, name in enumerate(
                    sm_names
                ):

                    if name.endswith(
                        "__treated"
                    ):

                        sm_treatment_index = (
                            index
                        )
                        break

                if (
                    sm_treatment_index
                    is not None
                ):

                    coefficient = float(
                        sm_model.params.iloc[sm_treatment_index]
                    )

                    se_beta = float(
                        sm_model.bse.iloc[sm_treatment_index]
                    )

                    odds_ratio = float(
                        np.exp(
                            coefficient
                        )
                    )

                    odds_ratio_ci_low = float(
                        np.exp(
                            coefficient
                            - 1.96
                            * se_beta
                        )
                    )

                    odds_ratio_ci_high = float(
                        np.exp(
                            coefficient
                            + 1.96
                            * se_beta
                        )
                    )

                    p_value = float(
                        sm_model.pvalues.iloc[sm_treatment_index]
                    )

            except Exception:
                pass

        except Exception:
            pass

    # --------------------------------------------------------
    # Interpretation
    # --------------------------------------------------------

    interpretation = (
        "Strong observational association. "
        "A randomized holdout is recommended "
        "before claiming causal impact."
    )

    return {
        "campaign_id": campaign_id,
        "treated_captains": int(
            treated_n
        ),
        "control_captains": int(
            control_n
        ),
        "treated_approval_rate": (
            float(
                treated_rate
            )
            if np.isfinite(
                treated_rate
            )
            else None
        ),
        "control_approval_rate": (
            float(
                control_rate
            )
            if np.isfinite(
                control_rate
            )
            else None
        ),
        "observed_lift_pp": (
            float(
                observed_lift * 100
            )
            if np.isfinite(
                observed_lift
            )
            else None
        ),
        "observed_lift_ci_low_pp": (
            float(
                ci_low * 100
            )
            if np.isfinite(
                ci_low
            )
            else None
        ),
        "observed_lift_ci_high_pp": (
            float(
                ci_high * 100
            )
            if np.isfinite(
                ci_high
            )
            else None
        ),
        "adjusted_treated_probability": (
            float(
                adjusted_treated_probability
            )
            if np.isfinite(
                adjusted_treated_probability
            )
            else None
        ),
        "adjusted_control_probability": (
            float(
                adjusted_control_probability
            )
            if np.isfinite(
                adjusted_control_probability
            )
            else None
        ),
        "adjusted_lift_pp": (
            float(
                adjusted_lift * 100
            )
            if np.isfinite(
                adjusted_lift
            )
            else None
        ),
        "log_odds_coefficient": (
            float(
                coefficient
            )
            if np.isfinite(
                coefficient
            )
            else None
        ),
        "odds_ratio": (
            float(
                odds_ratio
            )
            if np.isfinite(
                odds_ratio
            )
            else None
        ),
        "odds_ratio_ci_low": (
            float(
                odds_ratio_ci_low
            )
            if np.isfinite(
                odds_ratio_ci_low
            )
            else None
        ),
        "odds_ratio_ci_high": (
            float(
                odds_ratio_ci_high
            )
            if np.isfinite(
                odds_ratio_ci_high
            )
            else None
        ),
        "p_value": (
            float(
                p_value
            )
            if np.isfinite(
                p_value
            )
            else None
        ),
        "model_observations": int(
            len(base)
        ),
        "interpretation": interpretation,
    }


# ============================================================
# B2 - AIRPORT TRIP BEHAVIOUR
# ============================================================

def analyze_airport_trip_behavior(
    airport_trips: pd.DataFrame,
):
    """
    Analyse airport-origin trip behaviour.

    airport_trips does not contain captain_id, so this cannot
    measure individual captain retention.

    We therefore use:

        - cancellation
        - return fare within 20 minutes
        - fare
        - distance
        - fare per km

    as behavioural/economic proxies.
    """

    if airport_trips.empty:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
        )

    df = airport_trips.copy()

    if "request_ts" in df.columns:

        df["request_ts"] = pd.to_datetime(
            df["request_ts"],
            errors="coerce",
        )

        df["hour"] = (
            df["request_ts"]
            .dt.hour
        )

    else:
        df["hour"] = np.nan

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

    # --------------------------------------------------------
    # Overall
    # --------------------------------------------------------

    overall = pd.DataFrame(
        [
            {
                "trip_count": len(df),
                "cancellation_rate": (
                    df[
                        "captain_cancelled"
                    ].mean()
                    if "captain_cancelled"
                    in df.columns
                    else np.nan
                ),
                "return_fare_rate": (
                    df[
                        "got_return_fare_within_20min"
                    ].mean()
                    if (
                        "got_return_fare_within_20min"
                        in df.columns
                    )
                    else np.nan
                ),
                "avg_fare_inr": (
                    df[
                        "fare_inr"
                    ].mean()
                    if "fare_inr"
                    in df.columns
                    else np.nan
                ),
                "avg_distance_km": (
                    df[
                        "trip_distance_km"
                    ].mean()
                    if "trip_distance_km"
                    in df.columns
                    else np.nan
                ),
            }
        ]
    )

    if (
        "avg_fare_inr" in overall.columns
        and "avg_distance_km"
        in overall.columns
    ):

        overall[
            "avg_fare_per_km"
        ] = _safe_divide(
            overall[
                "avg_fare_inr"
            ],
            overall[
                "avg_distance_km"
            ],
        )

    # --------------------------------------------------------
    # Hourly
    # --------------------------------------------------------

    hourly = (
        df.groupby("hour")
        .agg(
            trip_count=(
                "trip_distance_km",
                "size",
            ),
            cancellation_rate=(
                "captain_cancelled",
                "mean",
            ),
            return_fare_rate=(
                "got_return_fare_within_20min",
                "mean",
            ),
            avg_fare_inr=(
                "fare_inr",
                "mean",
            ),
            avg_distance_km=(
                "trip_distance_km",
                "mean",
            ),
        )
        .reset_index()
    )

    hourly[
        "avg_fare_per_km"
    ] = _safe_divide(
        hourly[
            "avg_fare_inr"
        ],
        hourly[
            "avg_distance_km"
        ],
    )

    hourly = hourly.sort_values(
        "hour"
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # Destination type
    # --------------------------------------------------------

    if "drop_zone_type" in df.columns:

        destination = (
            df.groupby(
                "drop_zone_type"
            )
            .agg(
                trip_count=(
                    "trip_distance_km",
                    "size",
                ),
                cancellation_rate=(
                    "captain_cancelled",
                    "mean",
                ),
                return_fare_rate=(
                    "got_return_fare_within_20min",
                    "mean",
                ),
                avg_fare_inr=(
                    "fare_inr",
                    "mean",
                ),
                avg_distance_km=(
                    "trip_distance_km",
                    "mean",
                ),
            )
            .reset_index()
        )

        destination[
            "avg_fare_per_km"
        ] = _safe_divide(
            destination[
                "avg_fare_inr"
            ],
            destination[
                "avg_distance_km"
            ],
        )

        destination = (
            destination
            .sort_values(
                "trip_count",
                ascending=False,
            )
            .reset_index(
                drop=True
            )
        )

    else:
        destination = pd.DataFrame()

    return (
        overall,
        hourly,
        destination,
    )


# ============================================================
# B3 - AIRPORT SUPPLY GAP
# ============================================================

def calculate_airport_supply_gap(
    airport_hourly: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate airport supply gap by hour.

    IMPORTANT CORRECTION:

    The raw airport data contains separate rows for airport
    terminals such as T1 and T2.

    We MUST aggregate them first:

        total requests
        total fulfilled requests
        total online captains

    Then calculate:

        fulfilment rate
        requests per online captain

    We must NOT average row-level ratios.

    Benchmark:
        75th percentile of airport hourly fulfilment rate.

    This is a scenario estimate, not a causal estimate.
    """

    if airport_hourly.empty:
        return pd.DataFrame()

    df = airport_hourly.copy()

    required_columns = {
        "zone_type",
        "requests",
        "fulfilled_requests",
        "unfulfilled_requests",
        "online_captains",
    }

    missing = (
        required_columns
        - set(df.columns)
    )

    if missing:
        raise ValueError(
            "airport_hourly is missing required columns: "
            + ", ".join(
                sorted(missing)
            )
        )

    # --------------------------------------------------------
    # Hour
    # --------------------------------------------------------

    if "hour" not in df.columns:

        if "hour_ts" not in df.columns:
            raise ValueError(
                "airport_hourly must contain "
                "'hour_ts' or 'hour'."
            )

        df["hour_ts"] = pd.to_datetime(
            df["hour_ts"],
            errors="coerce",
        )

        df["hour"] = (
            df["hour_ts"]
            .dt.hour
        )

    else:

        df["hour"] = pd.to_numeric(
            df["hour"],
            errors="coerce",
        )

    # --------------------------------------------------------
    # Numeric fields
    # --------------------------------------------------------

    numeric_columns = [
        "requests",
        "fulfilled_requests",
        "unfulfilled_requests",
        "online_captains",
        "avg_eta_min",
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    # --------------------------------------------------------
    # Airport terminals only
    # --------------------------------------------------------

    airport = df[
        df[
            "zone_type"
        ]
        .astype(str)
        .str.lower()
        .eq(
            "airport_terminal"
        )
    ].copy()

    if airport.empty:
        return pd.DataFrame()

    # --------------------------------------------------------
    # CRITICAL AGGREGATION
    #
    # T1 + T2 are combined FIRST.
    # --------------------------------------------------------

    aggregation = {
        "requests": (
            "requests",
            "sum",
        ),
        "fulfilled_requests": (
            "fulfilled_requests",
            "sum",
        ),
        "unfulfilled_requests": (
            "unfulfilled_requests",
            "sum",
        ),
        "online_captains": (
            "online_captains",
            "sum",
        ),
    }

    if "avg_eta_min" in airport.columns:

        aggregation[
            "avg_eta_min"
        ] = (
            "avg_eta_min",
            "mean",
        )

    hourly = (
        airport
        .groupby("hour")
        .agg(
            **aggregation
        )
        .reset_index()
    )

    # --------------------------------------------------------
    # Fulfilment rate
    # --------------------------------------------------------

    hourly[
        "fulfilment_rate"
    ] = _safe_divide(
        hourly[
            "fulfilled_requests"
        ],
        hourly[
            "requests"
        ],
    )

    # --------------------------------------------------------
    # Demand pressure
    #
    # Correct formula:
    #
    # total requests / total online captains
    # --------------------------------------------------------

    hourly[
        "requests_per_online_captain"
    ] = _safe_divide(
        hourly[
            "requests"
        ],
        hourly[
            "online_captains"
        ],
    )

    # --------------------------------------------------------
    # Benchmark
    # --------------------------------------------------------

    valid_rates = (
        hourly[
            "fulfilment_rate"
        ]
        .dropna()
    )

    if valid_rates.empty:
        return hourly

    benchmark = (
        valid_rates
        .quantile(
            0.75
        )
    )

    hourly[
        "benchmark_fulfilment_rate"
    ] = benchmark

    # --------------------------------------------------------
    # Target fulfilled demand
    # --------------------------------------------------------

    hourly[
        "target_fulfilled_requests"
    ] = (
        hourly[
            "requests"
        ]
        * benchmark
    )

    # --------------------------------------------------------
    # Additional requests required
    # --------------------------------------------------------

    hourly[
        "additional_requests_to_fulfill"
    ] = (
        hourly[
            "target_fulfilled_requests"
        ]
        - hourly[
            "fulfilled_requests"
        ]
    ).clip(
        lower=0
    )

    # --------------------------------------------------------
    # Estimated additional captains
    # --------------------------------------------------------

    hourly[
        "estimated_additional_captains"
    ] = _safe_divide(
        hourly[
            "additional_requests_to_fulfill"
        ],
        hourly[
            "requests_per_online_captain"
        ],
    )

    hourly["hour"] = (
        pd.to_numeric(
            hourly["hour"],
            errors="coerce",
        )
        .astype("Int64")
    )

    return (
        hourly
        .sort_values(
            "estimated_additional_captains",
            ascending=False,
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# B3 - AIRPORT RECOMMENDATION
# ============================================================

def build_airport_recommendation(
    airport_supply_gap: pd.DataFrame,
    trip_behavior_overall: Optional[
        pd.DataFrame
    ] = None,
    trip_behavior_hourly: Optional[
        pd.DataFrame
    ] = None,
) -> pd.DataFrame:
    """
    Build airport supply recommendation.

    Main logic:

        1. Identify largest supply-gap hours.
        2. Determine whether late-night hours dominate.
        3. Check return-fare economics.
        4. Check captain cancellation.
        5. Recommend targeted supply intervention before
           broad acquisition when the issue is concentrated
           in late-night airport operations.
    """

    if (
        airport_supply_gap is None
        or airport_supply_gap.empty
    ):
        return pd.DataFrame()

    gap = airport_supply_gap.copy()

    gap["hour"] = pd.to_numeric(
        gap["hour"],
        errors="coerce",
    )

    gap[
        "estimated_additional_captains"
    ] = pd.to_numeric(
        gap[
            "estimated_additional_captains"
        ],
        errors="coerce",
    )

    # --------------------------------------------------------
    # Highest-gap hours
    # --------------------------------------------------------

    top_gap = (
        gap
        .sort_values(
            "estimated_additional_captains",
            ascending=False,
        )
        .head(6)
    )

    top_hours = (
        top_gap[
            "hour"
        ]
        .dropna()
        .astype(int)
        .tolist()
    )

    # --------------------------------------------------------
    # Late-night window
    #
    # 21:00 through 03:00
    # --------------------------------------------------------

    late_night_hours = {
        21,
        22,
        23,
        0,
        1,
        2,
        3,
    }

    late_gap = gap[
        gap[
            "hour"
        ].isin(
            late_night_hours
        )
    ].copy()

    late_gap_captains = (
        late_gap[
            "estimated_additional_captains"
        ]
        .sum()
    )

    total_gap_captains = (
        gap[
            "estimated_additional_captains"
        ]
        .sum()
    )

    late_night_gap_share = (
        late_gap_captains
        / total_gap_captains
        if total_gap_captains > 0
        else np.nan
    )

    # --------------------------------------------------------
    # Trip economics
    # --------------------------------------------------------

    overall_return_fare_rate = np.nan
    overall_cancel_rate = np.nan

    if (
        trip_behavior_overall is not None
        and not trip_behavior_overall.empty
    ):

        row = (
            trip_behavior_overall
            .iloc[0]
        )

        if (
            "return_fare_rate"
            in row.index
        ):

            overall_return_fare_rate = (
                pd.to_numeric(
                    row[
                        "return_fare_rate"
                    ],
                    errors="coerce",
                )
            )

        if (
            "cancellation_rate"
            in row.index
        ):

            overall_cancel_rate = (
                pd.to_numeric(
                    row[
                        "cancellation_rate"
                    ],
                    errors="coerce",
                )
            )

    # --------------------------------------------------------
    # Late-night trip behaviour
    # --------------------------------------------------------

    late_return_fare_rate = np.nan
    late_cancel_rate = np.nan

    if (
        trip_behavior_hourly is not None
        and not trip_behavior_hourly.empty
        and "hour"
        in trip_behavior_hourly.columns
    ):

        trip_hourly = (
            trip_behavior_hourly.copy()
        )

        trip_hourly["hour"] = pd.to_numeric(
            trip_hourly["hour"],
            errors="coerce",
        )

        late_trip = trip_hourly[
            trip_hourly[
                "hour"
            ].isin(
                late_night_hours
            )
        ].copy()

        if not late_trip.empty:

            if (
                "return_fare_rate"
                in late_trip.columns
            ):

                late_return_fare_rate = (
                    late_trip[
                        "return_fare_rate"
                    ].mean()
                )

            if (
                "cancellation_rate"
                in late_trip.columns
            ):

                late_cancel_rate = (
                    late_trip[
                        "cancellation_rate"
                    ].mean()
                )

    # --------------------------------------------------------
    # Recommendation
    # --------------------------------------------------------

    if (
        np.isfinite(
            late_night_gap_share
        )
        and late_night_gap_share
        >= 0.50
    ):

        recommendation = (
            "Prioritize airport incentives and "
            "repositioning before broad targeted acquisition."
        )

        reason = (
            "The majority of the estimated airport supply "
            "gap is concentrated in late-night hours. "
        )

        if (
            np.isfinite(
                late_return_fare_rate
            )
            and late_return_fare_rate
            < 0.35
        ):

            reason += (
                "Late-night sampled trips also show weak "
                "return-fare availability, suggesting weaker "
                "round-trip economics for captains. "
            )

        if (
            np.isfinite(
                late_cancel_rate
            )
            and late_cancel_rate
            > 0.17
        ):

            reason += (
                "Captain cancellation is elevated during "
                "the same period. "
            )

        reason += (
            "Therefore, test supply positioning and "
            "economic interventions before scaling broad "
            "airport captain acquisition."
        )

    else:

        recommendation = (
            "Run targeted airport captain acquisition "
            "alongside supply-positioning experiments."
        )

        reason = (
            "The estimated airport gap is not sufficiently "
            "concentrated in a single time window, so "
            "targeted acquisition should be tested together "
            "with operational interventions."
        )

    result = pd.DataFrame(
        [
            {
                "recommendation": recommendation,
                "reason": reason,
                "top_gap_hours": ",".join(
                    str(hour)
                    for hour in top_hours
                ),
                "estimated_total_gap_captains": (
                    float(
                        total_gap_captains
                    )
                    if np.isfinite(
                        total_gap_captains
                    )
                    else None
                ),
                "late_night_gap_share": (
                    float(
                        late_night_gap_share
                    )
                    if np.isfinite(
                        late_night_gap_share
                    )
                    else None
                ),
                "overall_return_fare_rate": (
                    float(
                        overall_return_fare_rate
                    )
                    if np.isfinite(
                        overall_return_fare_rate
                    )
                    else None
                ),
                "late_night_return_fare_rate": (
                    float(
                        late_return_fare_rate
                    )
                    if np.isfinite(
                        late_return_fare_rate
                    )
                    else None
                ),
                "overall_cancellation_rate": (
                    float(
                        overall_cancel_rate
                    )
                    if np.isfinite(
                        overall_cancel_rate
                    )
                    else None
                ),
                "late_night_cancellation_rate": (
                    float(
                        late_cancel_rate
                    )
                    if np.isfinite(
                        late_cancel_rate
                    )
                    else None
                ),
                "measurement": (
                    "Run a controlled airport experiment "
                    "comparing targeted incentives/repositioning "
                    "with a control group. Measure fulfilment "
                    "rate, unfulfilled requests, ETA, captain "
                    "online hours, cancellation rate and "
                    "incentive ROI."
                ),
            }
        ]
    )

    return result


# ============================================================
# JSON UTILITY
# ============================================================

def save_json(
    data: dict,
    output_path: str,
) -> None:
    """
    Save dictionary as formatted JSON.
    """

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )
        