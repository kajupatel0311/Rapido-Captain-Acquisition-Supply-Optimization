
import json

from src.config import (
    create_output_directories,
    TABLES_DIR,
    RESULTS_DIR,
)

from src.data_loader import load_all_data

from src.data_quality.audit import (
    audit_all,
    referential_integrity_checks,
    document_event_checks,
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
    campaign_confidence_analysis,
    analyze_airport_trip_behavior,
    calculate_airport_supply_gap,
    build_airport_recommendation,
)


def save_dataframe(df, path):
    """
    Save a DataFrame to CSV if it exists and is not empty.
    """
    if df is None:
        return

    if hasattr(df, "empty") and df.empty:
        return

    df.to_csv(
        path,
        index=False,
    )


def save_json(data, path):
    """
    Save a Python dictionary as JSON.
    """
    if data is None:
        return

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


def main():

    print("=" * 70)
    print("RAPIDO DATA SCIENCE TAKE-HOME")
    print("=" * 70)

    # --------------------------------------------------------
    # Create output directories
    # --------------------------------------------------------

    create_output_directories()

    # ========================================================
    # 1. LOAD DATA
    # ========================================================

    print("\n[1/8] Loading raw data...")

    data = load_all_data()

    for name, df in data.items():
        print(
            f"{name:20s}: {len(df):,} rows"
        )

    # ========================================================
    # 2. DATA QUALITY AUDIT
    # ========================================================

    print(
        "\n[2/8] Running data quality audit..."
    )

    profile = audit_all(data)

    save_dataframe(
        profile,
        RESULTS_DIR / "data_profile.csv",
    )

    integrity = referential_integrity_checks(
        data
    )

    save_dataframe(
        integrity,
        RESULTS_DIR / "referential_integrity.csv",
    )

    event_checks = document_event_checks(
        data["doc_events"]
    )

    save_dataframe(
        event_checks,
        RESULTS_DIR / "document_event_checks.csv",
    )

    # ========================================================
    # 3. ONBOARDING FUNNEL
    # ========================================================

    print(
        "\n[3/8] Building onboarding funnel..."
    )

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

    # --------------------------------------------------------
    # Document failure analysis
    # --------------------------------------------------------

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

    print("\nOnboarding funnel:")

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

    if campaign_results["observed"]:

        save_json(
            campaign_results["observed"],
            RESULTS_DIR / "campaign_observed.json",
        )

    if campaign_results["adjusted"]:

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

    # ========================================================
    # 6. BASIC ANALYSIS COMPLETE
    # ========================================================

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

    # --------------------------------------------------------
    # A3 — CAMPAIGN CONFIDENCE ANALYSIS
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
        "\nOutputs written to:"
    )

    print(
        RESULTS_DIR
    )

    print(
        TABLES_DIR
    )

    print(
        "\nNew decision-analysis files:"
    )

    print(
        "  A2:"
    )
    print(
        "    - a2_stage_segments.csv"
    )
    print(
        "    - a2_segment_leaks.csv"
    )
    print(
        "    - a2_actionable_segments.csv"
    )
    print(
        "    - a2_approval_opportunity.csv"
    )

    print(
        "  A3:"
    )
    print(
        "    - campaign_confidence.json"
    )

    print(
        "  B2:"
    )
    print(
        "    - b2_airport_trip_overall.csv"
    )
    print(
        "    - b2_airport_trip_hourly.csv"
    )
    print(
        "    - b2_airport_trip_destination.csv"
    )

    print(
        "  B3:"
    )
    print(
        "    - b3_airport_supply_gap.csv"
    )
    print(
        "    - b3_airport_recommendation.csv"
    )

    print(
        "\nPipeline completed successfully."
    )


if __name__ == "__main__":
    main()
    