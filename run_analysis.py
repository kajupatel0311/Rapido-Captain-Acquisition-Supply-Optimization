import json
from pathlib import Path

from src.config import (
    create_output_directories,
    TABLES_DIR,
    RESULTS_DIR,
)

from src.data_loader import load_all_data

from src.data_quality.audit import (
    run_data_quality_audit,
)

from src.preprocessing.clean import (
    clean_captains,
    clean_doc_events,
    clean_approvals,
    clean_activation,
    clean_airport_hourly,
)

from src.preprocessing.master_table import (
    build_master_table,
    add_funnel_features,
    save_master_table,
)

from src.onboarding.funnel import (
    build_funnel,
    funnel_summary,
    document_funnel_summary,
)

from src.onboarding.leak_analysis import (
    calculate_failure_reasons,
    calculate_document_dropoff,
)

from src.campaign.campaign_analysis import (
    prepare_campaign_data,
    campaign_report,
)

from src.airport.airport_analysis import (
    prepare_airport_hourly,
    airport_hourly_summary,
    airport_zone_summary,
    prepare_airport_trips,
)

from src.decision.decision_analysis import (
    build_stage_segment_table,
    summarize_segment_leaks,
    identify_actionable_segments,
    estimate_incremental_approvals,
    summarize_a2_opportunity,
    campaign_confidence_analysis,
    build_ranked_recommendations,
    build_simple_intervention_table,
    save_intervention_priority,
    analyze_airport_trip_behavior,
    calculate_airport_supply_gap,
    build_airport_recommendation,
)


DATA_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


def save_dataframe(df, path):
    """
    Save a non-empty DataFrame to CSV.
    """
    if df is None:
        return

    if hasattr(df, "empty") and df.empty:
        return

    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        path,
        index=False,
    )


def save_json(data, path):
    """
    Save a Python object as JSON.
    """
    if data is None:
        return

    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            default=str,
        )


def run_data_quality_gate(data):
    """
    Run the existing data-quality audit against the raw data.

    The audit reports data-quality problems separately from
    analytical cleaning. It does not silently remove records.
    """

    report = run_data_quality_audit(
        DATA_DIR
    )

    normalized_report = {
        "cutoff_date": "2026-06-30 23:59:59",
        "datasets_checked": report.get(
            "datasets_checked",
            0,
        ),
        "issue_count": report.get(
            "total_issues",
            0,
        ),
        "issues": report.get(
            "issues",
            [],
        ),
    }

    save_json(
        normalized_report,
        RESULTS_DIR / "data_quality_report.json",
    )

    return normalized_report


def build_clean_master_table(data):
    """
    Build cleaned datasets and a reusable captain-level
    analytical master table.
    """

    captains = clean_captains(
        data["captains"]
    )

    doc_events = clean_doc_events(
        data["doc_events"]
    )

    approvals = clean_approvals(
        data["approvals"]
    )

    activation = clean_activation(
        data["activation"]
    )

    airport_hourly = clean_airport_hourly(
        data["airport_hourly"]
    )

    save_dataframe(
        captains,
        PROCESSED_DIR / "captains_clean.csv",
    )

    save_dataframe(
        doc_events,
        PROCESSED_DIR / "doc_events_clean.csv",
    )

    save_dataframe(
        approvals,
        PROCESSED_DIR / "approvals_clean.csv",
    )

    save_dataframe(
        activation,
        PROCESSED_DIR / "activation_clean.csv",
    )

    save_dataframe(
        airport_hourly,
        PROCESSED_DIR / "airport_hourly_clean.csv",
    )

    master = build_master_table(
        captains=captains,
        doc_events=doc_events,
        approvals=approvals,
        activation=activation,
    )

    master = add_funnel_features(
        master
    )

    save_master_table(
        master,
        PROCESSED_DIR / "captain_master.csv",
    )

    return master


def run_decision_engine(
    actionable_segments,
    r2a_rate=0.383,
    recovery_rate=0.20,
):
    """
    Convert onboarding leakage into expected productive
    captain supply.

    This is explicitly scenario-based and not causal.
    """

    if actionable_segments is None:
        return None

    if actionable_segments.empty:
        return None

    priority = build_simple_intervention_table(
        actionable_segments,
        r2a_rate=r2a_rate,
        recovery_rate=recovery_rate,
    )

    save_intervention_priority(
        priority,
        TABLES_DIR / "intervention_priority.csv",
    )

    top_interventions = []

    for _, row in priority.head(10).iterrows():

        top_interventions.append(
            {
                "priority": str(
                    row.get(
                        "priority",
                        "P2",
                    )
                ),
                "city": str(
                    row.get(
                        "city",
                        "",
                    )
                ),
                "vehicle_type": str(
                    row.get(
                        "vehicle_type",
                        "",
                    )
                ),
                "acquisition_channel": str(
                    row.get(
                        "acquisition_channel",
                        "",
                    )
                ),
                "stage": str(
                    row.get(
                        "stage",
                        "",
                    )
                ),
                "expected_incremental_approvals": round(
                    float(
                        row.get(
                            "expected_incremental_approvals",
                            0,
                        )
                    ),
                    2,
                ),
                "expected_incremental_first_orders": round(
                    float(
                        row.get(
                            "expected_incremental_first_orders",
                            0,
                        )
                    ),
                    2,
                ),
            }
        )

    summary = {
        "objective": (
            "maximize expected productive "
            "captain supply"
        ),
        "assumed_recovery_rate": recovery_rate,
        "approval_to_first_order_rate": r2a_rate,
        "interpretation": (
            "Scenario-based prioritization, "
            "not causal impact."
        ),
        "top_interventions": top_interventions,
    }

    save_json(
        summary,
        RESULTS_DIR / "intervention_priority.json",
    )

    return priority


def main():

    print("=" * 70)
    print("RAPIDO DATA SCIENCE TAKE-HOME")
    print("Captain Acquisition & Supply Optimization")
    print("=" * 70)

    # ========================================================
    # 0. INITIALIZE
    # ========================================================

    create_output_directories()

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ========================================================
    # 1. LOAD DATA
    # ========================================================

    print(
        "\n[1/8] Loading raw data..."
    )

    data = load_all_data()

    for name, df in data.items():

        print(
            f"{name:20s}: {len(df):,} rows"
        )

    # ========================================================
    # 2. DATA QUALITY + PREPROCESSING
    # ========================================================

    print(
        "\n[2/8] Running data quality validation..."
    )

    quality_report = run_data_quality_gate(
        data
    )

    print(
        "Quality issues detected:",
        quality_report["issue_count"],
    )

    print(
        "\nBuilding cleaned captain master table..."
    )

    captain_master = build_clean_master_table(
        data
    )

    print(
        "Captain master table:",
        f"{len(captain_master):,} rows",
    )

    # ========================================================
    # 3. ONBOARDING FUNNEL
    # ========================================================

    print(
        "\n[3/8] Building onboarding funnel..."
    )

    # Correct business rule:
    #
    # Auto/Cab       -> Permit required
    # ERickshaw      -> Permit skipped

    funnel, document_state = build_funnel(
        data["captains"],
        data["doc_events"],
        data["approvals"],
        activation=data["activation"],
    )

    summary = funnel_summary(
        funnel
    )

    document_summary = document_funnel_summary(
        document_state
    )

    save_dataframe(
        funnel,
        RESULTS_DIR / "captain_funnel_base.csv",
    )

    save_dataframe(
        document_state,
        RESULTS_DIR / "document_state.csv",
    )

    save_dataframe(
        summary,
        TABLES_DIR / "onboarding_funnel.csv",
    )

    save_dataframe(
        document_summary,
        TABLES_DIR / "document_funnel.csv",
    )

    failure_reasons = calculate_failure_reasons(
        data["doc_events"]
    )

    save_dataframe(
        failure_reasons,
        TABLES_DIR / "document_failure_reasons.csv",
    )

    document_dropoff = calculate_document_dropoff(
        funnel,
        document_state,
    )

    save_dataframe(
        document_dropoff,
        TABLES_DIR / "document_dropoff.csv",
    )

    print(
        "\nOnboarding funnel:"
    )

    print(
        summary.to_string(
            index=False
        )
    )

    # ========================================================
    # 4. CAMPAIGN ANALYSIS
    # ========================================================

    print(
        "\n[4/8] Evaluating CAMP_WA_002..."
    )

    campaign_df = prepare_campaign_data(
        data["captains"],
        data["approvals"],
        data["nudges"],
    )

    campaign_results = campaign_report(
        campaign_df
    )

    save_dataframe(
        campaign_results["descriptive"],
        TABLES_DIR / "campaign_descriptive.csv",
    )

    if campaign_results.get("observed"):
        save_json(
            campaign_results["observed"],
            RESULTS_DIR / "campaign_observed.json",
        )

    if campaign_results.get("adjusted"):
        save_json(
            campaign_results["adjusted"],
            RESULTS_DIR / "campaign_adjusted.json",
        )

    # ========================================================
    # 5. AIRPORT MARKETPLACE ANALYSIS
    # ========================================================

    print(
        "\n[5/8] Analyzing airport supply..."
    )

    airport_hourly = prepare_airport_hourly(
        data["airport_hourly"]
    )

    airport_zones = airport_zone_summary(
        data["airport_hourly"]
    )

    airport_by_hour = airport_hourly_summary(
        data["airport_hourly"]
    )

    save_dataframe(
        airport_hourly,
        RESULTS_DIR / "airport_hourly_prepared.csv",
    )

    save_dataframe(
        airport_zones,
        TABLES_DIR / "airport_zone_summary.csv",
    )

    save_dataframe(
        airport_by_hour,
        TABLES_DIR / "airport_hourly_summary.csv",
    )

    airport_trips = prepare_airport_trips(
        data["airport_trips"]
    )

    save_dataframe(
        airport_trips,
        RESULTS_DIR / "airport_trips_prepared.csv",
    )

    print(
        "\n[6/8] Analysis preparation complete."
    )

    # ========================================================
    # 7. DECISION ANALYSIS
    # ========================================================

    print(
        "\n[7/8] Running decision analysis..."
    )

    # --------------------------------------------------------
    # A2 — SEGMENT-LEVEL ONBOARDING LEAKAGE
    # --------------------------------------------------------

    print(
        "\n  A2: Building onboarding segment analysis..."
    )
    print(
        "    - a2_opportunity_summary.csv"
    )

    stage_segments = build_stage_segment_table(
        data["captains"],
        data["doc_events"],
        data["approvals"],
    )

    segment_leaks = summarize_segment_leaks(
        stage_segments
    )

    actionable_segments = (
        identify_actionable_segments(
            segment_leaks
        )
    )

    approval_opportunity = (
        estimate_incremental_approvals(
            actionable_segments,
            data["approvals"],
            improvement_rate=0.20,
            stage_segment_table=stage_segments,
        )
    )

    save_dataframe(
        stage_segments,
        RESULTS_DIR / "a2_stage_segments.csv",
    )

    save_dataframe(
        segment_leaks,
        TABLES_DIR / "a2_segment_leaks.csv",
    )

    save_dataframe(
        actionable_segments,
        TABLES_DIR / "a2_actionable_segments.csv",
    )

    save_dataframe(
        approval_opportunity,
        TABLES_DIR / "a2_approval_opportunity.csv",
    )

    a2_opportunity_summary = summarize_a2_opportunity(
        approval_opportunity
        )

    save_dataframe(
        a2_opportunity_summary,
        TABLES_DIR / "a2_opportunity_summary.csv",
    )

    # --------------------------------------------------------
    # DECISION ENGINE
    # --------------------------------------------------------

    print(
        "\n  Decision Engine: ranking interventions..."
    )

    intervention_priority = run_decision_engine(
        actionable_segments,
        r2a_rate=0.383,
        recovery_rate=0.20,
    )

    if intervention_priority is not None:
        print(
            "  Intervention priority generated."
        )

    # --------------------------------------------------------
    # A3 — CAMPAIGN CONFIDENCE
    # --------------------------------------------------------

    print(
        "\n  A3: Calculating campaign confidence..."
    )

    campaign_confidence = (
        campaign_confidence_analysis(
            data["captains"],
            data["approvals"],
            data["nudges"],
        )
    )

    save_json(
        campaign_confidence,
        RESULTS_DIR / "campaign_confidence.json",
    )

    # --------------------------------------------------------
    # A4 — RANKED RECOMMENDATIONS
    # --------------------------------------------------------

    print(
        "\n  A4: Building ranked recommendations..."
    )

    # Approved count is taken from the cleaned approval table.
    # First-order count is taken from activation data.
    # The calculation below is a planning scenario, not a causal forecast.

    approved_count = 0

    if "final_status" in data["approvals"].columns:
        approved_count = int(
            data["approvals"]["final_status"]
            .astype(str)
            .str.strip()
            .str.lower()
            .eq("approved")
            .sum()
        )

    first_order_count = 0

    activation_df = data["activation"]

    if "first_order_completed" in activation_df.columns:
        values = activation_df["first_order_completed"]

        if values.dtype == bool:
            first_order_count = int(values.sum())
        else:
            normalized = (
                values.astype(str)
                .str.strip()
                .str.lower()
            )

            first_order_count = int(
                normalized.isin(
                    {
                        "true",
                        "1",
                        "yes",
                        "y",
                        "completed",
                        "complete",
                    }
                ).sum()
            )

    elif "first_order_ts" in activation_df.columns:
        first_order_count = int(
            activation_df["first_order_ts"]
            .notna()
            .sum()
        )

    elif "first_order_time" in activation_df.columns:
        first_order_count = int(
            activation_df["first_order_time"]
            .notna()
            .sum()
        )

    a4_ranked_recommendations = build_ranked_recommendations(
        approval_opportunity=approval_opportunity,
        campaign_confidence=campaign_confidence,
        approved_count=approved_count,
        first_order_count=first_order_count,
        permit_recovery_rate=0.20,
        r2a_improvement_pp=5.0,
    )

    save_dataframe(
        a4_ranked_recommendations,
        TABLES_DIR / "a4_ranked_recommendations.csv",
    )

    print(
        "\n  A4 ranked recommendations:"
    )

    print(
        a4_ranked_recommendations.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # B2 — AIRPORT TRIP BEHAVIOR
    # --------------------------------------------------------

    print(
        "\n  B2: Analyzing airport trip behavior..."
    )

    (
        trip_overall,
        trip_hourly,
        trip_destination,
    ) = analyze_airport_trip_behavior(
        data["airport_trips"]
    )

    save_dataframe(
        trip_overall,
        TABLES_DIR / "b2_airport_trip_overall.csv",
    )

    save_dataframe(
        trip_hourly,
        TABLES_DIR / "b2_airport_trip_hourly.csv",
    )

    save_dataframe(
        trip_destination,
        TABLES_DIR / "b2_airport_trip_destination.csv",
    )

    # --------------------------------------------------------
    # B3 — AIRPORT SUPPLY GAP
    # --------------------------------------------------------

    print(
        "\n  B3: Calculating airport supply gap..."
    )

    airport_supply_gap = (
        calculate_airport_supply_gap(
            data["airport_hourly"]
        )
    )

    save_dataframe(
        airport_supply_gap,
        TABLES_DIR / "b3_airport_supply_gap.csv",
    )

    airport_recommendation = (
        build_airport_recommendation(
            airport_supply_gap,
            trip_overall,
            trip_hourly,
        )
    )

    save_dataframe(
        airport_recommendation,
        TABLES_DIR / "b3_airport_recommendation.csv",
    )

    # ========================================================
    # 8. FINAL OUTPUT
    # ========================================================

    print(
        "\n[8/8] Decision analysis complete."
    )

    print(
        "\nOutputs:"
    )

    print(
        f"  Results: {RESULTS_DIR}"
    )

    print(
        f"  Tables:  {TABLES_DIR}"
    )

    print(
        "\nOptimization outputs:"
    )

    print(
        "  - data/processed/captains_clean.csv"
    )

    print(
        "  - data/processed/doc_events_clean.csv"
    )

    print(
        "  - data/processed/approvals_clean.csv"
    )

    print(
        "  - data/processed/activation_clean.csv"
    )

    print(
        "  - data/processed/airport_hourly_clean.csv"
    )

    print(
        "  - data/processed/captain_master.csv"
    )

    print(
        "  - outputs/results/data_quality_report.json"
    )

    print(
        "  - outputs/results/intervention_priority.json"
    )

    print(
        "  - outputs/tables/intervention_priority.csv"
    )

    print(
        "  - outputs/tables/a2_opportunity_summary.csv"
    )

    print(
        "  - outputs/tables/a4_ranked_recommendations.csv"
    )

    print(
        "\nPipeline completed successfully."
    )


if __name__ == "__main__":
    main()