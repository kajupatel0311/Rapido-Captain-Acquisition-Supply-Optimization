import pandas as pd


DOCUMENTS = [
    "DL",
    "RC",
    "AADHAAR",
    "PERMIT",
    "FITNESS",
    "INSURANCE",
]


def build_document_status(doc_events):
    """
    Build captain-level document clearance flags.

    A document is considered cleared when a captain has at least
    one verification_pass event for that document.
    """

    events = doc_events.copy()

    events["doc_type"] = (
        events["doc_type"]
        .astype("string")
        .str.upper()
        .str.strip()
    )

    events["event_type"] = (
        events["event_type"]
        .astype("string")
        .str.lower()
        .str.strip()
    )

    events = events[
        events["doc_type"].isin(DOCUMENTS)
    ].copy()

    passed = events[
        events["event_type"] == "verification_pass"
    ].copy()

    # If there are no successful verification events,
    # return an empty captain-level status table.
    if passed.empty:

        result = pd.DataFrame(
            {
                "captain_id": pd.Series(
                    dtype="string"
                )
            }
        )

        for document in DOCUMENTS:
            result[f"{document}_cleared"] = pd.Series(
                dtype="int8"
            )

        return result

    # A captain/document pair is cleared if at least
    # one successful verification exists.
    status = (
        passed[
            [
                "captain_id",
                "doc_type",
            ]
        ]
        .drop_duplicates()
        .copy()
    )

    status["cleared"] = 1

    # Convert document types into columns.
    status = status.pivot(
        index="captain_id",
        columns="doc_type",
        values="cleared",
    )

    # Guarantee the exact six expected document columns.
    status = status.reindex(
        columns=DOCUMENTS,
        fill_value=0,
    )

    # At this point missing values mean the document
    # was not cleared.
    status = (
        status
        .fillna(0)
        .astype("int8")
    )

    status.columns = [
        f"{column}_cleared"
        for column in status.columns
    ]

    return status.reset_index()


def build_master_table(
    captains,
    doc_events,
    approvals,
    activation,
):
    """
    Build a reusable captain-level analytical master table.

    Combines:
        1. Captain signup information
        2. Document clearance status
        3. Approval status
        4. Activation / first-order information
    """

    master = captains.copy()

    # ========================================================
    # 1. DOCUMENT STATUS
    # ========================================================

    document_status = build_document_status(
        doc_events
    )

    master = master.merge(
        document_status,
        on="captain_id",
        how="left",
        sort=False,
    )

    # ========================================================
    # 2. APPROVAL STATUS
    # ========================================================

    approvals = approvals.copy()

    if "approval_status" in approvals.columns:

        approval_data = approvals[
            [
                "captain_id",
                "approval_status",
            ]
        ].copy()

    elif "status" in approvals.columns:

        approval_data = approvals[
            [
                "captain_id",
                "status",
            ]
        ].copy()

        approval_data = approval_data.rename(
            columns={
                "status": "approval_status"
            }
        )

    else:

        approval_data = approvals[
            [
                "captain_id"
            ]
        ].copy()

        approval_data["approval_status"] = (
            pd.NA
        )

    # Normalize approval status.
    approval_data["approval_status"] = (
        approval_data["approval_status"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    # Ensure one approval record per captain.
    approval_data = (
        approval_data
        .drop_duplicates(
            subset=["captain_id"],
            keep="last",
        )
    )

    master = master.merge(
        approval_data,
        on="captain_id",
        how="left",
        sort=False,
    )

    # Guarantee the column exists.
    if "approval_status" not in master.columns:

        master["approval_status"] = (
            pd.Series(
                pd.NA,
                index=master.index,
                dtype="string",
            )
        )

    master["approval_status"] = (
        master["approval_status"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    # ========================================================
    # 3. ACTIVATION / FIRST-ORDER DATA
    # ========================================================

    if (
        activation is not None
        and not activation.empty
        and "captain_id" in activation.columns
    ):

        activation = activation.copy()

        activation_columns = [
            column
            for column in activation.columns
            if column != "captain_id"
        ]

        if activation_columns:

            activation_data = activation[
                [
                    "captain_id"
                ] + activation_columns
            ].copy()

            activation_data = (
                activation_data
                .drop_duplicates(
                    subset=["captain_id"],
                    keep="last",
                )
            )

            master = master.merge(
                activation_data,
                on="captain_id",
                how="left",
                sort=False,
            )

    # ========================================================
    # 4. DOCUMENT FLAGS
    # ========================================================

    for document in DOCUMENTS:

        column = f"{document}_cleared"

        if column not in master.columns:

            master[column] = 0

        else:

            # The left merge creates missing values for
            # captains who have no document status row.
            #
            # Convert to an ordinary numeric Series first,
            # explicitly replace missing values with zero,
            # then convert to int8.
            numeric_values = pd.to_numeric(
                master[column],
                errors="coerce",
            )

            numeric_values = numeric_values.fillna(
                0
            )

            # Use NumPy-backed values rather than pandas'
            # nullable integer array.
            master[column] = pd.Series(
                numeric_values.to_numpy(
                    dtype="int8"
                ),
                index=master.index,
            )

    # ========================================================
    # 5. APPROVAL FLAG
    # ========================================================

    master["approved_flag"] = (
        master["approval_status"]
        .eq("approved")
        .fillna(False)
        .astype("int8")
    )

    return master


def add_funnel_features(master):
    """
    Add document and approval funnel features.

    Business rule:

        Auto       -> Permit required
        Cab        -> Permit required
        ERickshaw  -> Permit skipped
    """

    df = master.copy()

    # --------------------------------------------------------
    # Normalize vehicle type
    # --------------------------------------------------------

    df["vehicle_type"] = (
        df["vehicle_type"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    # --------------------------------------------------------
    # Permit requirement
    # --------------------------------------------------------

    df["permit_required"] = (
        df["vehicle_type"].isin(
            [
                "auto",
                "cab",
            ]
        )
    )

    # --------------------------------------------------------
    # All documents cleared
    # --------------------------------------------------------

    df["all_documents_cleared"] = (
        df["DL_cleared"].eq(1)
        & df["RC_cleared"].eq(1)
        & df["AADHAAR_cleared"].eq(1)
        & (
            (~df["permit_required"])
            | df["PERMIT_cleared"].eq(1)
        )
        & df["FITNESS_cleared"].eq(1)
        & df["INSURANCE_cleared"].eq(1)
    ).astype("int8")

    return df


def save_master_table(
    master,
    path="data/processed/captain_master.csv",
):
    """
    Save the captain-level master table.
    """

    master.to_csv(
        path,
        index=False,
    )
