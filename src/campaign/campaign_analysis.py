import pandas as pd
import numpy as np
import statsmodels.formula.api as smf


CAMPAIGN_ID = "CAMP_WA_002"


def prepare_campaign_data(
    captains,
    approvals,
    nudges,
):
    captains = captains.copy()
    approvals = approvals.copy()
    nudges = nudges.copy()

    captains["signup_ts"] = pd.to_datetime(
        captains["signup_ts"],
        errors="coerce",
    )

    approvals["decision_ts"] = pd.to_datetime(
        approvals["decision_ts"],
        errors="coerce",
    )

    nudges["sent_ts"] = pd.to_datetime(
        nudges["sent_ts"],
        errors="coerce",
    )

    campaign = nudges[
        nudges["campaign_id"] == CAMPAIGN_ID
    ].copy()

    first_campaign = (
        campaign
        .sort_values("sent_ts")
        .groupby("captain_id", as_index=False)
        .first()
    )

    base = captains.merge(
        approvals[
            [
                "captain_id",
                "decision_ts",
                "final_status",
            ]
        ],
        on="captain_id",
        how="left",
    )

    base = base.merge(
        first_campaign[
            [
                "captain_id",
                "sent_ts",
                "delivered",
                "clicked",
            ]
        ],
        on="captain_id",
        how="left",
    )

    base["campaign_received"] = (
        base["sent_ts"].notna()
    )

    base["approved"] = (
        base["final_status"] == "approved"
    )

    base["signup_month"] = (
        base["signup_ts"]
        .dt.to_period("M")
        .astype(str)
    )

    return base


def descriptive_campaign_result(df):
    result = (
        df.groupby("campaign_received")
        .agg(
            captains=("captain_id", "nunique"),
            approved=("approved", "sum"),
        )
        .reset_index()
    )

    result["approval_rate"] = (
        result["approved"]
        / result["captains"]
    )

    return result


def calculate_observed_lift(df):
    grouped = (
        df.groupby("campaign_received")
        ["approved"]
        .mean()
    )

    treated = grouped.get(True, np.nan)
    control = grouped.get(False, np.nan)

    return {
        "treated_approval_rate": treated,
        "control_approval_rate": control,
        "observed_lift_pp": (
            (treated - control) * 100
            if pd.notna(treated)
            and pd.notna(control)
            else np.nan
        ),
    }


def adjusted_logistic_model(df):
    model_df = df.copy()

    model_df["campaign"] = (
        model_df["campaign_received"]
        .astype(int)
    )

    model_df["approved_binary"] = (
        model_df["approved"]
        .astype(int)
    )

    possible_features = [
        "city",
        "vehicle_type",
        "acquisition_channel",
        "device_tier",
        "app_language",
        "age_band",
        "signup_month",
    ]

    features = [
        c for c in possible_features
        if c in model_df.columns
        and model_df[c].notna().any()
    ]

    model_df = model_df.dropna(
        subset=[
            "approved_binary",
            "campaign",
        ] + features
    )

    if model_df["campaign"].nunique() < 2:
        return None, None

    formula_parts = [
        "campaign"
    ]

    for feature in features:
        formula_parts.append(
            f"C({feature})"
        )

    formula = (
        "approved_binary ~ "
        + " + ".join(formula_parts)
    )

    model = smf.logit(
        formula,
        data=model_df,
    ).fit(
        disp=False
    )

    return model, model_df


def campaign_report(df):
    descriptive = descriptive_campaign_result(df)

    observed = calculate_observed_lift(df)

    model, model_df = adjusted_logistic_model(df)

    adjusted = None

    if model is not None:
        treated = model_df.copy()
        control = model_df.copy()

        treated["campaign"] = 1
        control["campaign"] = 0

        treated_probability = model.predict(
            treated
        ).mean()

        control_probability = model.predict(
            control
        ).mean()

        adjusted = {
            "adjusted_treated_probability":
                treated_probability,
            "adjusted_control_probability":
                control_probability,
            "adjusted_lift_pp":
                (
                    treated_probability
                    - control_probability
                ) * 100,
        }

    return {
        "descriptive": descriptive,
        "observed": observed,
        "adjusted": adjusted,
        "model": model,
    }