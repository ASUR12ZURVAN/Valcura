import json
import os
import datetime
from typing import Tuple, Dict, Any, Optional
import requests

class GoogleSheetsService:
    """
    Service to handle syncing responses and logs to Google Sheets.
    Supports both Google Cloud Service Account (gspread) and Google Apps Script Webhook API.
    """

    def __init__(self):
        self.spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
        self.service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "google_credentials.json")
        self.service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        self.webhook_url = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL")

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
