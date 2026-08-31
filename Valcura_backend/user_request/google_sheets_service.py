import json
import os
import datetime
from typing import Tuple, Dict, Any, Optional, List
import requests

class GoogleSheetsService:
    """
    Service to handle syncing responses and logs to Google Sheets.
    Supports both Google Cloud Service Account (gspread) and Google Apps Script Webhook API.
    Also supports reading patient status data for automated workflow triggering.
    """

    def __init__(self):
        self.spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
        self.service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "google_credentials.json")
        self.service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        self.webhook_url = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL")
        self.patient_sheet_name = os.getenv("GOOGLE_SHEETS_PATIENT_SHEET", "Patient Status")

    def append_row(
        self,
        phone_number: str,
        source: str,
        user_message: str,
        ai_response: str,
        status: str = "Received",
        timestamp: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Appends a response/log row to Google Sheets.
        Returns (success: bool, message: str)
        """
        if not timestamp:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row_data = {
            "timestamp": timestamp,
            "phone_number": phone_number,
            "source": source,
            "user_message": user_message or "",
            "ai_response": ai_response or "",
            "status": status
        }

        # Priority 1: Google Apps Script Webhook URL if configured
        if self.webhook_url:
            return self._send_via_webhook(row_data)

        # Priority 2: Google Service Account (gspread / Google Sheets API)
        if self.spreadsheet_id and (os.path.exists(self.service_account_file) or self.service_account_json):
            return self._send_via_gspread(row_data)

        return False, "Google Sheets setup missing. Configure GOOGLE_SHEETS_WEBHOOK_URL or GOOGLE_SERVICE_ACCOUNT_FILE in .env."

    def _send_via_webhook(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Sends data payload to Google Apps Script Web App Webhook."""
        try:
            response = requests.post(
                self.webhook_url,
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            if response.status_code in [200, 201, 302]:
                return True, "Successfully synced to Google Sheets via Webhook"
            else:
                return False, f"Webhook returned HTTP {response.status_code}: {response.text}"
        except Exception as e:
            return False, f"Google Sheets Webhook error: {str(e)}"

    def _send_via_gspread(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Appends row using gspread library and Google Service Account."""
        try:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]

            if self.service_account_json:
                creds_dict = json.loads(self.service_account_json)
                creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            elif os.path.exists(self.service_account_file):
                creds = Credentials.from_service_account_file(self.service_account_file, scopes=scopes)
            else:
                return False, "Service account credentials file not found."

            client = gspread.authorize(creds)
            sheet = client.open_by_key(self.spreadsheet_id).sheet1

            row_values = [
                data["timestamp"],
                data["phone_number"],
                data["source"],
                data["user_message"],
                data["ai_response"],
                data["status"]
            ]

            sheet.append_row(row_values)
            return True, "Successfully appended row to Google Sheet via API"
        except ImportError:
            return False, "gspread or google-auth package not installed. Run: pip install gspread google-auth"
        except Exception as e:
            return False, f"gspread error: {str(e)}"

    def read_patient_status(self) -> Tuple[bool, List[Dict[str, Any]], str]:
        """
        Reads patient status data from the Google Sheets.
        Returns (success: bool, patient_data: List[Dict], message: str)
        """
        if not self.spreadsheet_id:
            return False, [], "GOOGLE_SHEETS_SPREADSHEET_ID not configured in .env"

        try:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]

            if self.service_account_json:
                creds_dict = json.loads(self.service_account_json)
                creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            elif os.path.exists(self.service_account_file):
                creds = Credentials.from_service_account_file(self.service_account_file, scopes=scopes)
            else:
                return False, [], "Service account credentials file not found."

            client = gspread.authorize(creds)
            spreadsheet = client.open_by_key(self.spreadsheet_id)
            
            # Try to get the patient status sheet
            try:
                sheet = spreadsheet.worksheet(self.patient_sheet_name)
            except gspread.WorksheetNotFound:
                # Fallback to first sheet if patient sheet not found
                sheet = spreadsheet.sheet1

            # Get all data
            all_data = sheet.get_all_records()
            
            # Process and normalize patient data
            patient_data = []
            for row in all_data:
                if self._is_valid_patient_row(row):
                    patient_data.append(self._normalize_patient_row(row))

            return True, patient_data, f"Successfully read {len(patient_data)} patient records"

        except ImportError:
            return False, [], "gspread or google-auth package not installed. Run: pip install gspread google-auth"
        except Exception as e:
            return False, [], f"Google Sheets read error: {str(e)}"

    def get_patient_by_phone(self, phone_number: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Get a specific patient's status by phone number.
        Returns (success: bool, patient_data: Optional[Dict], message: str)
        """
        success, all_patients, message = self.read_patient_status()
        if not success:
            return False, None, message

        # Normalize phone number for comparison
        normalized_phone = self._normalize_phone_number(phone_number)
        
        for patient in all_patients:
            patient_phone = self._normalize_phone_number(patient.get('phone_number', ''))
            if patient_phone == normalized_phone:
                return True, patient, "Patient found"

        return False, None, f"Patient with phone number {phone_number} not found"

    def get_patients_by_status(self, status: str) -> Tuple[bool, List[Dict[str, Any]], str]:
        """
        Get all patients with a specific status.
        Returns (success: bool, patient_data: List[Dict], message: str)
        """
        success, all_patients, message = self.read_patient_status()
        if not success:
            return False, [], message

        filtered_patients = [
            patient for patient in all_patients 
            if patient.get('status', '').lower() == status.lower()
        ]

        return True, filtered_patients, f"Found {len(filtered_patients)} patients with status '{status}'"

    def get_patients_requiring_followup(self) -> Tuple[bool, List[Dict[str, Any]], str]:
        """
        Get patients who require follow-up based on their status and last contact date.
        Returns (success: bool, patient_data: List[Dict], message: str)
        """
        success, all_patients, message = self.read_patient_status()
        if not success:
            return False, [], message

        followup_patients = []
        today = datetime.datetime.now()

        for patient in all_patients:
            status = patient.get('status', '').lower()
            last_contact_str = patient.get('last_contact_date', '')
            
            # Check if patient needs follow-up based on status
            if status in ['new', 'inquiry', 'consultation_scheduled', 'treatment_discussed']:
                followup_patients.append(patient)
            elif last_contact_str:
                try:
                    last_contact = datetime.datetime.strptime(last_contact_str, "%Y-%m-%d")
                    days_since_contact = (today - last_contact).days
                    
                    # Follow up if no contact in 3+ days
                    if days_since_contact >= 3:
                        patient['days_since_contact'] = days_since_contact
                        followup_patients.append(patient)
                except ValueError:
                    pass

        return True, followup_patients, f"Found {len(followup_patients)} patients requiring follow-up"

    def update_patient_status(self, phone_number: str, status: str, notes: str = "") -> Tuple[bool, str]:
        """
        Update a patient's status in the Google Sheets.
        Returns (success: bool, message: str)
        """
        if not self.spreadsheet_id:
            return False, "GOOGLE_SHEETS_SPREADSHEET_ID not configured in .env"

        try:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]

            if self.service_account_json:
                creds_dict = json.loads(self.service_account_json)
                creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            elif os.path.exists(self.service_account_file):
                creds = Credentials.from_service_account_file(self.service_account_file, scopes=scopes)
            else:
                return False, "Service account credentials file not found."

            client = gspread.authorize(creds)
            spreadsheet = client.open_by_key(self.spreadsheet_id)
            
            try:
                sheet = spreadsheet.worksheet(self.patient_sheet_name)
            except gspread.WorksheetNotFound:
                sheet = spreadsheet.sheet1

            # Find the row with the matching phone number
            all_data = sheet.get_all_records()
            phone_col_index = self._find_column_index(sheet, 'phone_number')
            
            if phone_col_index is None:
                return False, "phone_number column not found in sheet"

            row_number = None
            for i, row in enumerate(all_data, start=2):  # Start from row 2 (after header)
                row_phone = str(row.get('phone_number', ''))
                if self._normalize_phone_number(row_phone) == self._normalize_phone_number(phone_number):
                    row_number = i
                    break

            if row_number is None:
                return False, f"Patient with phone number {phone_number} not found"

            # Update the status and notes
            status_col_index = self._find_column_index(sheet, 'status')
            notes_col_index = self._find_column_index(sheet, 'notes')
            
            if status_col_index:
                sheet.update_cell(row_number, status_col_index, status)
            
            if notes_col_index and notes:
                current_notes = sheet.cell(row_number, notes_col_index).value
                updated_notes = f"{current_notes}\n{datetime.datetime.now().strftime('%Y-%m-%d')}: {notes}" if current_notes else notes
                sheet.update_cell(row_number, notes_col_index, updated_notes)

            return True, f"Successfully updated patient status for {phone_number}"

        except Exception as e:
            return False, f"Google Sheets update error: {str(e)}"

    def _is_valid_patient_row(self, row: Dict[str, Any]) -> bool:
        """Check if a row contains valid patient data."""
        return bool(row.get('phone_number') or row.get('Phone Number') or row.get('phone'))

    def _normalize_patient_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize patient data to standard field names."""
        normalized = {}
        
        # Common field name variations
        field_mappings = {
            'phone_number': ['phone_number', 'Phone Number', 'phone', 'Phone', 'contact', 'Contact'],
            'patient_name': ['patient_name', 'Patient Name', 'name', 'Name', 'patient', 'Patient'],
            'status': ['status', 'Status', 'current_status', 'Current Status'],
            'treatment': ['treatment', 'Treatment', 'treatment_type', 'Treatment Type'],
            'appointment_date': ['appointment_date', 'Appointment Date', 'appointment', 'Appointment'],
            'last_contact_date': ['last_contact_date', 'Last Contact Date', 'last_contact', 'Last Contact'],
            'notes': ['notes', 'Notes', 'comments', 'Comments'],
            'objection': ['objection', 'Objection', 'concern', 'Concern'],
            'library': ['library', 'Library', 'workflow_stage', 'Workflow Stage'],
        }

        for standard_name, variations in field_mappings.items():
            for variation in variations:
                if variation in row and row[variation]:
                    normalized[standard_name] = row[variation]
                    break
            if standard_name not in normalized:
                normalized[standard_name] = ""

        return normalized

    def _normalize_phone_number(self, phone_number: str) -> str:
        """Normalize phone number for comparison."""
        if not phone_number:
            return ""
        # Remove all non-numeric characters
        return ''.join(c for c in str(phone_number) if c.isdigit())

    def _find_column_index(self, sheet, column_name: str) -> Optional[int]:
        """Find the column index for a given column name."""
        try:
            header_row = sheet.row_values(1)
            for i, header in enumerate(header_row, start=1):
                if header.lower().replace(' ', '_') == column_name.lower().replace(' ', '_'):
                    return i
        except Exception:
            pass
        return None
