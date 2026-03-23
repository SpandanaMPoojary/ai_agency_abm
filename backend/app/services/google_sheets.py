import os
import gspread
from google.oauth2.service_account import Credentials
import logging

class GoogleSheetsService:
    def __init__(self):
        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        self.creds_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "service_account.json")
        self.spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")
        self.client = None

    def _authenticate(self):
        if not os.path.exists(self.creds_path):
            logging.error(f"Google Sheets credentials not found at {self.creds_path}")
            return False
        
        try:
            credentials = Credentials.from_service_account_file(self.creds_path, scopes=self.scopes)
            self.client = gspread.authorize(credentials)
            return True
        except Exception as e:
            logging.error(f"Failed to authenticate with Google Sheets: {e}")
            return False

    def append_lead(self, profile_url: str, message: str):
        """
        Appends a lead to the 'Approved_LinkedIn_Outreach' spreadsheet with deduplication.
        """
        if not self._authenticate():
            return {"status": "error", "message": "Google Sheets Authentication failed"}

        try:
            # Open the spreadsheet
            if self.spreadsheet_id:
                sheet = self.client.open_by_key(self.spreadsheet_id).sheet1
            else:
                # Fallback to name if ID not set
                sheet = self.client.open("Approved_LinkedIn_Outreach").sheet1

            # 1. Initialize headers if missing or wrong
            header_row = ["profileURL", "messagetobesent"]
            try:
                current_headers = sheet.row_values(1)
                if current_headers != header_row:
                    sheet.insert_row(header_row, index=1)
                    logging.info("Updated headers in Google Sheets.")
            except:
                sheet.append_row(header_row)
                logging.info("Created headers in empty Google Sheets.")

            # 2. Deduplication check
            existing_urls = sheet.col_values(1) # Column A
            if profile_url in existing_urls:
                logging.info(f"Lead {profile_url} already exists in Sheets. Skipping.")
                return {"status": "skipped", "message": "Lead already exists"}

            # 2. Append data
            sheet.append_row([profile_url, message])
            logging.info(f"Successfully appended lead {profile_url} to Google Sheets.")
            return {"status": "success"}

        except Exception as e:
            logging.error(f"Error appending to Google Sheets: {e}")
            return {"status": "error", "message": str(e)}
