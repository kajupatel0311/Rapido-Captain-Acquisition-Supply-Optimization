import pandas as pd

from src.config import (
    REQUIRED_DOCUMENTS_ALL,
    REQUIRED_DOCUMENTS_AUTO_CAB,
)


# ============================================================
# DOCUMENT NORMALIZATION
# ============================================================

DOCUMENT_NORMALIZATION = {
    "DL": "DL",
    "RC": "RC",
    "AADHAAR": "AADHAAR",
    "FITNESS": "FITNESS",
    "PERMIT": "PERMIT",
    "INSURANCE": "INSURANCE",
}


# ============================================================
# DOCUMENT ORDER
# ============================================================

BASE_DOCUMENT_ORDER = [
    "DL",
    "RC",
    "AADHAAR",
    "FITNESS",
    "INSURANCE",
]


# ============================================================
# REQUIRED DOCUMENTS
# ============================================================

def get_required_documents(vehicle_type):
    """
    Return required documents in onboarding order.

    Auto/Cab:

        DL
        RC
        AADHAAR
        PERMIT
        FITNESS
        INSURANCE

    Other vehicles:

        DL
        RC
        AADHAAR
        FITNESS
        INSURANCE
    """

    vehicle = str(
        vehicle_type
    ).strip().lower()

    documents = list(
        BASE_DOCUMENT_ORDER
    )

    # Permit is required for Auto and Cab only. Keep this rule explicit
    # instead of relying on REQUIRED_DOCUMENTS_AUTO_CAB, which represents
    # document requirements rather than vehicle types in some configs.
    permit_vehicles = {"auto", "cab"}

    if vehicle in permit_vehicles:
        documents.insert(
            3,
            "PERMIT",
        )

    return documents


# ============================================================
# NORMALIZE EVENTS
# ============================================================

def normalize_document_events(doc_events):
    """
    Normalize document and event fields.
    """

    df = doc_events[
        [
            "captain_id",
            "doc_type",
            "event_type",
            "event_ts",
        ]
    ].copy()

    df["doc_type"] = (
        df["doc_type"]
        .astype("string")
        .str.strip()
        .str.upper()
        .map(DOCUMENT_NORMALIZATION)
    )

    df["event_type"] = (
        df["event_type"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    return df


# ============================================================
# FIRST PASS LOOKUP
# ============================================================

def build_first_pass_lookup(doc_events):
    """
    Build:

        (captain_id, doc_type)
            ->
        earliest successful verification timestamp

    This is calculated ONCE.

    The old implementation repeatedly filtered the complete
    event dataframe for every captain/document combination.
    """

    df = normalize_document_events(
        doc_events
    )

    passes = df[
        (df["event_type"] == "verification_pass")
        & df["doc_type"].notna()
        & df["event_ts"].notna()
    ]

    # One sort for the entire dataset.
    passes = passes.sort_values(
        [
            "captain_id",
            "doc_type",
            "event_ts",
        ]
    )

    # One row per captain/document.
    first_pass = (
        passes
        .drop_duplicates(
            [
                "captain_id",
                "doc_type",
            ],
            keep="first",
        )
    )

    # Convert to a Series indexed by captain/document.
    lookup = (
        first_pass
        .set_index(
            [
                "captain_id",
                "doc_type",
            ]
        )["event_ts"]
        .to_dict()
    )

    return lookup


# ============================================================
# BUILD DOCUMENT STATE
# ============================================================

def build_document_state(
    captains,
    doc_events,
):
    """
    Build document-level clearance state.

    This answers:

        "Did this captain ever successfully clear this
         document?"

    It is used for document diagnostics and failure analysis.
    """

    lookup = build_first_pass_lookup(
        doc_events
    )

    captain_records = captains[
        [
            "captain_id",
            "city",
            "vehicle_type",
            "acquisition_channel",
            "device_tier",
            "app_language",
            "age_band",
        ]
    ].to_dict(
        orient="records"
    )

    rows = []

    for captain in captain_records:

        captain_id = captain[
            "captain_id"
        ]

        required_documents = (
            get_required_documents(
                captain["vehicle_type"]
            )
        )

        for doc_type in required_documents:

            pass_ts = lookup.get(
                (
                    captain_id,
                    doc_type,
                )
            )

            cleared = (
                pass_ts is not None
            )

            rows.append(
                {
                    "captain_id": captain_id,
                    "city": captain["city"],
                    "vehicle_type": captain[
                        "vehicle_type"
                    ],
                    "acquisition_channel": captain[
                        "acquisition_channel"
                    ],
                    "device_tier": captain[
                        "device_tier"
                    ],
                    "app_language": captain[
                        "app_language"
                    ],
                    "age_band": captain[
                        "age_band"
                    ],
                    "doc_type": doc_type,
                    "cleared": cleared,
                    "pass_ts": pass_ts,
                }
            )

    return pd.DataFrame(
        rows
    )


# ============================================================
# SEQUENTIAL FUNNEL
# ============================================================

def build_sequential_funnel(
    captains,
    doc_events,
    approvals,
    activation=None,
    document_state=None,
):
    """
    Build the logical sequential onboarding funnel.

    Permit is required only for Auto/Cab. ERickshaw therefore moves
    directly from Aadhaar to Fitness.

    A captain clears a stage only when the first successful verification
    for that document occurs after the previous required document was
    successfully verified. Retries are therefore handled naturally.

    If activation is supplied, First Order is added after Approved.
    """

    if document_state is None:
        document_state = build_document_state(
            captains,
            doc_events,
        )

    # First successful verification timestamp for each captain/document.
    first_pass_lookup = build_first_pass_lookup(doc_events)

    captain_base = captains[
        [
            "captain_id",
            "city",
            "vehicle_type",
            "acquisition_channel",
            "device_tier",
            "app_language",
            "age_band",
            "signup_ts",
        ]
    ].copy()

    captain_base["signup_ts"] = pd.to_datetime(
        captain_base["signup_ts"],
        errors="coerce",
    )

    # Approval status.
    approval_columns = ["captain_id", "decision_ts", "final_status"]
    approval_df = approvals[
        [c for c in approval_columns if c in approvals.columns]
    ].copy()

    if "decision_ts" in approval_df.columns:
        approval_df["decision_ts"] = pd.to_datetime(
            approval_df["decision_ts"],
            errors="coerce",
        )

    captain_base = captain_base.merge(
        approval_df,
        on="captain_id",
        how="left",
    )

    captain_base["approved"] = (
        captain_base["final_status"]
        .astype("string")
        .str.strip()
        .str.lower()
        .eq("approved")
    )

    # Activation is optional to preserve backward compatibility.
    if activation is not None and not activation.empty:
        activation_columns = [
            "captain_id",
            "first_order_ts",
        ]

        activation_df = activation[
            [c for c in activation_columns if c in activation.columns]
        ].copy()

        if "first_order_ts" in activation_df.columns:
            activation_df["first_order_ts"] = pd.to_datetime(
                activation_df["first_order_ts"],
                errors="coerce",
            )

        captain_base = captain_base.merge(
            activation_df,
            on="captain_id",
            how="left",
        )

        captain_base["first_order_completed"] = (
            captain_base["first_order_ts"].notna()
        )
    else:
        captain_base["first_order_completed"] = False

    rows = []

    for captain in captain_base.itertuples(index=False):
        captain_id = captain.captain_id
        vehicle = str(captain.vehicle_type).strip().lower()

        # Business rule: Permit is mandatory for Auto/Cab and skipped for
        # ERickshaw. Keep this explicit so the funnel cannot accidentally
        # treat the document-name config as a vehicle-type list.
        permit_required = vehicle in {"auto", "cab"}

        documents = get_required_documents(
            captain.vehicle_type
        )

        previous_pass_ts = None
        stage_flags = {}

        for doc_type in documents:
            pass_ts = first_pass_lookup.get(
                (
                    captain_id,
                    doc_type,
                )
            )

            if previous_pass_ts is None:
                cleared = pass_ts is not None
            else:
                cleared = (
                    pass_ts is not None
                    and pass_ts > previous_pass_ts
                )

            stage_flags[f"stage_{doc_type}"] = bool(cleared)

            if cleared:
                previous_pass_ts = pass_ts
            else:
                # Once a required stage is missed, all downstream
                # sequential stages are considered uncleared.
                previous_pass_ts = None
                break

        # Ensure all expected logical columns exist.
        for doc_type in [
            "DL",
            "RC",
            "AADHAAR",
            "PERMIT",
            "FITNESS",
            "INSURANCE",
        ]:
            stage_flags.setdefault(
                f"stage_{doc_type}",
                False,
            )

        # ERickshaw does not require Permit.
        if not permit_required:
            stage_flags["stage_PERMIT"] = stage_flags["stage_AADHAAR"]

        stage_flags["all_documents_cleared"] = bool(
            stage_flags["stage_INSURANCE"]
        )

        # Approved is a terminal business outcome. It should not be
        # inferred from document events alone.
        stage_flags["approved"] = bool(captain.approved)

        stage_flags["first_order_completed"] = bool(
            captain.first_order_completed
        )

        row = {
            "captain_id": captain_id,
            "city": captain.city,
            "vehicle_type": captain.vehicle_type,
            "acquisition_channel": captain.acquisition_channel,
            "device_tier": captain.device_tier,
            "app_language": captain.app_language,
            "age_band": captain.age_band,
            "signup_ts": captain.signup_ts,
            "signup_month": (
                captain.signup_ts.to_period("M")
                if pd.notna(captain.signup_ts)
                else pd.NaT
            ),
            "permit_required": permit_required,
        }

        row.update(stage_flags)
        rows.append(row)

    state = pd.DataFrame(rows)

    if state.empty:
        return (
            pd.DataFrame(),
            state,
        )

    # Keep signup_month as a clean string for CSV/groupby use.
    state["signup_month"] = (
        state["signup_month"]
        .astype("string")
    )

    # Logical funnel stages. Permit is already treated as a pass-through
    # for vehicles that do not require it.
    logical_stages = [
        ("Signup", pd.Series(True, index=state.index)),
        ("DL", state["stage_DL"]),
        ("RC", state["stage_RC"]),
        ("AADHAAR", state["stage_AADHAAR"]),
        ("PERMIT", state["stage_PERMIT"]),
        ("FITNESS", state["stage_FITNESS"]),
        ("INSURANCE", state["stage_INSURANCE"]),
        (
            "All Documents Cleared",
            state["all_documents_cleared"],
        ),
        ("Approved", state["approved"]),
    ]

    if activation is not None and not activation.empty:
        logical_stages.append(
            (
                "First Order Completed",
                state["first_order_completed"],
            )
        )

    funnel_rows = []
    signup_count = len(state)
    previous_count = None

    for stage_name, flag in logical_stages:
        count = int(flag.sum())

        if previous_count is None:
            lost = 0
            stage_conversion = 1.0
        else:
            lost = max(previous_count - count, 0)
            stage_conversion = (
                count / previous_count
                if previous_count > 0
                else 0.0
            )

        cumulative_conversion = (
            count / signup_count
            if signup_count > 0
            else 0.0
        )

        funnel_rows.append(
            {
                "stage": stage_name,
                "captains": count,
                "lost_from_previous_stage": int(lost),
                "stage_conversion": round(
                    stage_conversion,
                    6,
                ),
                "cumulative_conversion": round(
                    cumulative_conversion,
                    6,
                ),
            }
        )

        previous_count = count

    funnel = pd.DataFrame(funnel_rows)

    return funnel, state


# ============================================================
# MAIN FUNNEL FUNCTION
# ============================================================

def build_funnel(
    captains,
    doc_events,
    approvals,
    activation=None,
):
    """
    Main function expected by run_analysis.py.

    Returns:
        funnel
        document_state
    """

    # Build document state once and reuse it for diagnostics.
    document_state = build_document_state(
        captains,
        doc_events,
    )

    funnel, _ = build_sequential_funnel(
        captains,
        doc_events,
        approvals,
        activation=activation,
        document_state=document_state,
    )

    return (
        funnel,
        document_state,
    )


# ============================================================
# FUNNEL SUMMARY
# ============================================================

def funnel_summary(funnel):
    """
    Summarize an already-created funnel.

    Compatible with:

        funnel_summary(funnel)
    """

    columns = [
        "stage",
        "captains",
        "lost_from_previous_stage",
        "stage_conversion",
        "cumulative_conversion",
    ]

    return funnel[
        columns
    ].copy()


# ============================================================
# DOCUMENT SUMMARY
# ============================================================

def document_funnel_summary(
    document_state,
):
    """
    Summarize document-level clearance.

    This is a diagnostic table and should not be confused
    with the sequential onboarding funnel.
    """

    summary = (
        document_state
        .groupby("doc_type")
        .agg(
            captains_required=(
                "captain_id",
                "nunique",
            ),
            captains_cleared=(
                "cleared",
                "sum",
            ),
        )
        .reset_index()
    )

    summary["captains_cleared"] = (
        summary["captains_cleared"]
        .astype(int)
    )

    summary["not_cleared"] = (
        summary["captains_required"]
        - summary["captains_cleared"]
    )

    summary["clearance_rate"] = (
        summary["captains_cleared"]
        / summary["captains_required"]
    )

    return summary.sort_values(
        "clearance_rate"
    ).reset_index(
        drop=True
    )

