"""Create and seed the Google Sheet used by patient follow-up automation."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv


# This script only uses synthetic test patients. Replace them only when you are
# intentionally ready to write real patient data to the configured spreadsheet.
PATIENT_HEADERS = [
    "patient_id",
    "patient_name",
    "phone_number",
    "status",
    "treatment",
    "appointment_date",
    "last_contact_date",
    "objection",
    "library",
    "notes",
]

TEST_PATIENTS = [
    [
        "TEST-PATIENT-001",
        "Aarav Mehta",
        "+919876543210",
        "new",
        "Dental consultation",
        "",
        "2026-09-07",
        "",
        "Library 1",
        "Synthetic test record - safe to delete",
    ],
    [
        "TEST-PATIENT-002",
        "Diya Shah",
        "+919876543211",
        "consultation_scheduled",
        "Root Canal Treatment",
        "2026-09-10",
        "2026-09-06",
        "",
        "Library 3",
        "Synthetic test record - safe to delete",
    ],
    [
        "TEST-PATIENT-003",
        "Kabir Rao",
        "+919876543212",
        "treatment_discussed",
        "Dental implant",
        "",
        "2026-09-01",
        "cost",
        "Library 5",
        "Synthetic test record - safe to delete",
    ],
]


def load_credentials():
    """Build Google credentials from the configured file or inline JSON."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as error:
        raise RuntimeError(
            "Install the Google Sheets dependencies first: "
            "pip install gspread google-auth"
        ) from error

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    inline_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    credential_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "google_credentials.json")

    if inline_json:
        return gspread, Credentials.from_service_account_info(
            json.loads(inline_json), scopes=scopes
        )

    credential_path = Path(credential_file)
    if not credential_path.is_absolute():
        credential_path = Path(__file__).resolve().parents[1] / credential_path

    if not credential_path.exists():
        raise FileNotFoundError(
            f"Google service-account file not found: {credential_path}. "
            "Place it there or set GOOGLE_SERVICE_ACCOUNT_JSON."
        )

    return gspread, Credentials.from_service_account_file(
        credential_path, scopes=scopes
    )


def setup_patient_sheet() -> None:
    """Create the configured worksheet, headers, and synthetic test records."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")

    spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
    worksheet_name = os.getenv("GOOGLE_SHEETS_PATIENT_SHEET", "Patient Status")
    if not spreadsheet_id:
        raise RuntimeError("GOOGLE_SHEETS_SPREADSHEET_ID is missing from .env")

    gspread, credentials = load_credentials()
    spreadsheet = gspread.authorize(credentials).open_by_key(spreadsheet_id)

    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        # Create the worksheet instead of silently writing to the wrong tab.
        worksheet = spreadsheet.add_worksheet(
            title=worksheet_name,
            rows=max(len(TEST_PATIENTS) + 1, 100),
            cols=len(PATIENT_HEADERS),
        )

    existing_headers = worksheet.row_values(1)
    if existing_headers and existing_headers != PATIENT_HEADERS:
        raise RuntimeError(
            f"Worksheet '{worksheet_name}' already has different headers. "
            "Review it manually before adding test data."
        )

    if not existing_headers:
        worksheet.update(range_name="A1", values=[PATIENT_HEADERS])

    existing_rows = worksheet.get_all_values()
    existing_patient_ids = {
        row[0] for row in existing_rows[1:] if row and row[0]
    }
    rows_to_add = [
        row for row in TEST_PATIENTS if row[0] not in existing_patient_ids
    ]
    if rows_to_add:
        worksheet.append_rows(rows_to_add, value_input_option="USER_ENTERED")

    print(f"Worksheet ready: {worksheet_name}")
    print(f"Synthetic rows added: {len(rows_to_add)}")


if __name__ == "__main__":
    setup_patient_sheet()