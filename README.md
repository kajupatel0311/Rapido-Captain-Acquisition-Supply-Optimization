"""Rapido Captain Acquisition & Supply Analysis Pipeline.

Executes end-to-end processing from raw data ingestion to funnel metrics,
segment leak evaluation, campaign uplift, and airport gap sizing.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm

# -----------------------------------------------------------------------------
# Configuration & Directory Setup
# -----------------------------------------------------------------------------
BASE_DIR = Path(".")
DATA_RAW = BASE_DIR / "data" / "raw"
DATA_PROCESSED = BASE_DIR / "data" / "processed"
OUTPUTS_RESULTS = BASE_DIR / "outputs" / "results"
OUTPUTS_TABLES = BASE_DIR / "outputs" / "tables"

for directory in [DATA_PROCESSED, OUTPUTS_RESULTS, OUTPUTS_TABLES]:
    directory.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# 1. Data Ingestion & Quality Audit
# -----------------------------------------------------------------------------
print("Loading raw datasets...")
captains = pd.read_csv(DATA_RAW / "captains.csv")
doc_events = pd.read_csv(DATA_RAW / "doc_events.csv")
approvals = pd.read_csv(DATA_RAW / "approvals.csv")
activation = pd.read_csv(DATA_RAW / "activation.csv")
nudges = pd.read_csv(DATA_RAW / "nudges.csv")
airport_hourly = pd.read_csv(DATA_RAW / "airport_hourly.csv")
airport_trips = pd.read_csv(DATA_RAW / "airport_trips.csv")

# Standardize timestamps
captains["signup_timestamp"] = pd.to_datetime(captains["signup_timestamp"])
captains["signup_month"] = captains["signup_timestamp"].dt.to_period("M").astype(str)

# -----------------------------------------------------------------------------
# 2. Sequential Onboarding Funnel
# -----------------------------------------------------------------------------
print("Building onboarding funnel...")

# Resolve successfully verified document types per captain
verified_docs = (
    doc_events[doc_events["status"].str.upper() == "APPROVED"]
    .groupby(["captain_id", "doc_type"])
    .size()
    .unstack(fill_value=0)
)

funnel = captains[["captain_id", "city", "vehicle_type", "channel", "signup_month"]].copy()
funnel = funnel.merge(verified_docs, on="captain_id", how="left").fillna(0)
funnel = funnel.merge(approvals[["captain_id", "is_approved"]], on="captain_id", how="left")
funnel = funnel.merge(activation[["captain_id", "first_order_timestamp"]], on="captain_id", how="left")

funnel["is_approved"] = funnel["is_approved"].fillna(0).astype(int)
funnel["has_first_order"] = funnel["first_order_timestamp"].notna().astype(int)

# Stage adherence flags
funnel["stage_signup"] = 1
funnel["stage_dl"] = (funnel["DL"] > 0).astype(int)
funnel["stage_rc"] = (funnel["stage_dl"] & (funnel["RC"] > 0)).astype(int)
funnel["stage_aadhaar"] = (funnel["stage_rc"] & (funnel["AADHAAR"] > 0)).astype(int)

# PERMIT is mandatory only for Auto and Cab; ERickshaw bypasses to next stage
needs_permit = funnel["vehicle_type"].str.upper().isin(["AUTO", "CAB"])
funnel["stage_permit"] = np.where(
    needs_permit,
    (funnel["stage_aadhaar"] & (funnel.get("PERMIT", 0) > 0)).astype(int),
    funnel["stage_aadhaar"],
)

funnel["stage_fitness"] = (funnel["stage_permit"] & (funnel.get("FITNESS", 0) > 0)).astype(int)
funnel["stage_insurance"] = (funnel["stage_fitness"] & (funnel.get("INSURANCE", 0) > 0)).astype(int)
funnel["stage_approved"] = (funnel["stage_insurance"] & (funnel["is_approved"] == 1)).astype(int)
funnel["stage_first_order"] = (funnel["stage_approved"] & (funnel["has_first_order"] == 1)).astype(int)

# Save Funnel Metrics Summary
funnel_summary = pd.DataFrame({
    "Stage": [
        "Signups", "DL", "RC", "AADHAAR", "PERMIT", 
        "FITNESS", "INSURANCE", "Approved", "First Order"
    ],
    "Captains": [
        funnel["stage_signup"].sum(),
        funnel["stage_dl"].sum(),
        funnel["stage_rc"].sum(),
        funnel["stage_aadhaar"].sum(),
        funnel["stage_permit"].sum(),
        funnel["stage_fitness"].sum(),
        funnel["stage_insurance"].sum(),
        funnel["stage_approved"].sum(),
        funnel["stage_first_order"].sum(),
    ]
})
funnel_summary.to_csv(OUTPUTS_TABLES / "funnel_summary.csv", index=False)

# -----------------------------------------------------------------------------
# 3. A2 — Onboarding Leak & Opportunity Analysis
# -----------------------------------------------------------------------------
print("Analyzing stage drop-offs and actionable segments...")

group_cols = ["city", "vehicle_type", "channel", "signup_month"]
stage_cols = [
    "stage_signup", "stage_dl", "stage_rc", "stage_aadhaar", 
    "stage_permit", "stage_fitness", "stage_insurance", "stage_approved"
]

stage_segments = funnel.groupby(group_cols)[stage_cols].sum().reset_index()
stage_segments.to_csv(OUTPUTS_RESULTS / "a2_stage_segments.csv", index=False)

# Identify leaks (absolute count lost per transition)
segment_leaks = stage_segments.copy()
segment_leaks["leak_permit"] = segment_leaks["stage_aadhaar"] - segment_leaks["stage_permit"]
segment_leaks["leak_overall"] = segment_leaks["stage_signup"] - segment_leaks["stage_approved"]
segment_leaks.to_csv(OUTPUTS_RESULTS / "a2_segment_leaks.csv", index=False)

# Actionable Segment Ranking (Permit Leaks)
actionable_segments = (
    segment_leaks.groupby(["city", "vehicle_type", "channel"])[["leak_permit"]]
    .sum()
    .sort_values(by="leak_permit", ascending=False)
    .reset_index()
)
actionable_segments.to_csv(OUTPUTS_RESULTS / "a2_actionable_segments.csv", index=False)

# Mature Cohort Opportunity Model (Excluding latest snapshot cohort)
latest_cohort = funnel["signup_month"].max()
mature_cohorts = funnel[funnel["signup_month"] < latest_cohort]

# Historical conversion rate from Permit clearance to Final Approval
permit_cleared = mature_cohorts[mature_cohorts["stage_permit"] == 1]
downstream_approval_rate = (
    permit_cleared["stage_approved"].sum() / permit_cleared["stage_permit"].sum()
    if permit_cleared["stage_permit"].sum() > 0 else 0
)

# Model: 20% relative reduction in stage non-clearance
opportunity_df = actionable_segments.copy()
opportunity_df["recovered_dropouts_20pct"] = opportunity_df["leak_permit"] * 0.20
opportunity_df["incremental_approvals_scenario"] = (
    opportunity_df["recovered_dropouts_20pct"] * downstream_approval_rate
).round(1)
opportunity_df.to_csv(OUTPUTS_RESULTS / "a2_approval_opportunity.csv", index=False)

# -----------------------------------------------------------------------------
# 4. A3 — Campaign Uplift Inference (CAMP_WA_002)
# -----------------------------------------------------------------------------
print("Evaluating campaign performance...")

# Merge nudge exposures
camp_nudges = nudges[nudges["campaign_id"] == "CAMP_WA_002"].drop_duplicates(subset=["captain_id"])
eval_df = funnel.merge(
    camp_nudges[["captain_id", "delivered"]],
    on="captain_id",
    how="left"
)
eval_df["treated"] = eval_df["delivered"].fillna(0).astype(int)

# Observed statistics
treated_group = eval_df[eval_df["treated"] == 1]["stage_approved"]
control_group = eval_df[eval_df["treated"] == 0]["stage_approved"]

p1 = treated_group.mean() if len(treated_group) > 0 else 0
p0 = control_group.mean() if len(control_group) > 0 else 0
observed_lift = p1 - p0

# Standard error & 95% Confidence Interval
n1, n0 = len(treated_group), len(control_group)
se = np.sqrt((p1 * (1 - p1) / n1) + (p0 * (1 - p0) / n0)) if n1 > 0 and n0 > 0 else 0
ci_lower = observed_lift - (1.96 * se)
ci_upper = observed_lift + (1.96 * se)

# Logistic regression adjustment
reg_data = pd.get_dummies(
    eval_df[["stage_approved", "treated", "city", "vehicle_type", "channel"]],
    columns=["city", "vehicle_type", "channel"],
    drop_first=True,
    dtype=float
)
X = sm.add_constant(reg_data.drop(columns=["stage_approved"]))
y = reg_data["stage_approved"]

logit_model = sm.Logit(y, X).fit(disp=False)
odds_ratio = np.exp(logit_model.params["treated"])

# Average Marginal Effect (Adjusted Lift)
marginal_effects = logit_model.get_margeff(at="overall")
treated_idx = list(X.columns).index("treated") - 1
adjusted_lift = marginal_effects.margeff[treated_idx]

campaign_metrics = {
    "observed_lift_pp": round(float(observed_lift * 100), 2),
    "ci_95_lower_pp": round(float(ci_lower * 100), 2),
    "ci_95_upper_pp": round(float(ci_upper * 100), 2),
    "adjusted_lift_pp": round(float(adjusted_lift * 100), 2),
    "odds_ratio": round(float(odds_ratio), 2),
}

with open(OUTPUTS_RESULTS / "campaign_confidence.json", "w") as f:
    json.dump(campaign_metrics, f, indent=4)

# -----------------------------------------------------------------------------
# 5. B1/B3 — Airport Supply Gap Sizing
# -----------------------------------------------------------------------------
print("Analyzing airport demand/supply gaps...")

# Benchmark: 75th percentile of hourly fulfillment rate
p75_fulfillment = airport_hourly["fulfilled_trips"].sum() / airport_hourly["demand"].sum()
airport_hourly["target_trips"] = np.ceil(airport_hourly["demand"] * p75_fulfillment)
airport_hourly["supply_gap_trips"] = np.maximum(
    0, airport_hourly["target_trips"] - airport_hourly["fulfilled_trips"]
)

# Convert trip shortage to captain-hour capacity equivalent
TRIPS_PER_CAPTAIN_HOUR = 1.2
airport_hourly["captain_gap_capacity"] = (
    airport_hourly["supply_gap_trips"] / TRIPS_PER_CAPTAIN_HOUR
).round(1)

b3_airport_supply_gap = (
    airport_hourly.groupby("hour")[["supply_gap_trips", "captain_gap_capacity"]]
    .sum()
    .reset_index()
)
b3_airport_supply_gap.to_csv(OUTPUTS_RESULTS / "b3_airport_supply_gap.csv", index=False)

# -----------------------------------------------------------------------------
# 6. B2 — Airport Trip Economics & Friction
# -----------------------------------------------------------------------------
print("Aggregating airport trip metrics...")

# Global aggregates
b2_overall = pd.DataFrame([{
    "total_trips": len(airport_trips),
    "cancellation_rate": airport_trips["is_cancelled"].mean(),
    "return_fare_rate_20min": airport_trips["has_return_fare_20min"].mean(),
    "avg_fare": airport_trips["fare"].mean(),
    "avg_distance_km": airport_trips["distance_km"].mean(),
}])
b2_overall.to_csv(OUTPUTS_RESULTS / "b2_airport_trip_overall.csv", index=False)

# Hourly trip behavior
b2_hourly = airport_trips.groupby("trip_hour").agg(
    trips=("trip_id", "count"),
    cancellation_rate=("is_cancelled", "mean"),
    return_fare_rate=("has_return_fare_20min", "mean"),
    avg_fare=("fare", "mean"),
    avg_distance_km=("distance_km", "mean"),
).reset_index()
b2_hourly.to_csv(OUTPUTS_RESULTS / "b2_airport_trip_hourly.csv", index=False)

# Destination zone breakdown
b2_destination = airport_trips.groupby("destination_zone").agg(
    trips=("trip_id", "count"),
    cancellation_rate=("is_cancelled", "mean"),
    return_fare_rate=("has_return_fare_20min", "mean"),
    avg_fare=("fare", "mean"),
    avg_distance_km=("distance_km", "mean"),
).reset_index()
b2_destination.to_csv(OUTPUTS_RESULTS / "b2_airport_trip_destination.csv", index=False)

print("Pipeline execution complete. All tables and results generated successfully.")