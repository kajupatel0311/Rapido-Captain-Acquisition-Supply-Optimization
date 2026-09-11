from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ============================================================
# DATA DIRECTORIES
# ============================================================

DATA_DIR = PROJECT_ROOT / "data"

RAW_DATA_DIR = DATA_DIR / "raw"

PROCESSED_DATA_DIR = DATA_DIR / "processed"


# ============================================================
# OUTPUT DIRECTORIES
# ============================================================

OUTPUT_DIR = PROJECT_ROOT / "outputs"

TABLES_DIR = OUTPUT_DIR / "tables"

RESULTS_DIR = OUTPUT_DIR / "results"

CHARTS_DIR = OUTPUT_DIR / "charts"


# ============================================================
# RAW DATA FILES
# ============================================================

RAW_FILES = {
    "captains": RAW_DATA_DIR / "captains.csv",
    "doc_events": RAW_DATA_DIR / "doc_events.csv",
    "approvals": RAW_DATA_DIR / "approvals.csv",
    "activation": RAW_DATA_DIR / "activation.csv",
    "nudges": RAW_DATA_DIR / "nudges.csv",
    "airport_hourly": RAW_DATA_DIR / "airport_hourly.csv",
    "airport_trips": RAW_DATA_DIR / "airport_trips.csv",
}


# ============================================================
# DATA EXTRACTION
# ============================================================

EXTRACTION_TS = "2026-06-30 23:59:00"


# ============================================================
# ONBOARDING RULES
# ============================================================

MAX_DOCUMENT_ATTEMPTS = 3


# All captains require these documents.
REQUIRED_DOCUMENTS_ALL = [
    "DL",
    "RC",
    "AADHAAR",
    "FITNESS",
    "INSURANCE",
]


# Auto and Cab additionally require Permit.
REQUIRED_DOCUMENTS_AUTO_CAB = [
    "PERMIT",
]


# ============================================================
# OUTPUT DIRECTORY CREATION
# ============================================================

def create_output_directories():
    """
    Create all directories required by the analysis.
    """

    directories = [
        OUTPUT_DIR,
        TABLES_DIR,
        RESULTS_DIR,
        CHARTS_DIR,
        PROCESSED_DATA_DIR,
    ]

    for directory in directories:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )


        