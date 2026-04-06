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

    def append_lead(self, profile_url: str, first_name: str, connection_note: str):
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

            logging.info(f"Connected to sheet: {sheet.title}")

            # 1. Initialize headers if missing or wrong
            header_row = ["profileUrl", "firstName", "connectionNote"]
            try:
                current_headers = sheet.row_values(1)
                if not current_headers or current_headers != header_row:
                    logging.info(f"Updating headers from {current_headers} to {header_row}")
                    # If wrong headers, clear and insert or just update row 1
                    if len(current_headers) > 0:
                        sheet.update('A1:C1', [header_row])
                    else:
                        sheet.insert_row(header_row, index=1)
                    logging.info("Successfully updated headers in Google Sheets.")
            except Exception as e:
                logging.warning(f"Header update failed or sheet empty: {e}")
                sheet.append_row(header_row)

            # 2. Deduplication check
            try:
                existing_urls = sheet.col_values(1) # Column A
                if profile_url in existing_urls:
                    logging.info(f"Lead {profile_url} already exists in Sheets. Skipping.")
                    return {"status": "skipped", "message": "Lead already exists"}
            except Exception as e:
                logging.error(f"Deduplication check failed: {e}")

            # 3. Append data
            row_data = [profile_url, first_name, connection_note]
            sheet.append_row(row_data)
            logging.info(f"Successfully appended lead {profile_url} with data: {row_data}")
            return {"status": "success"}

        except Exception as e:
            logging.error(f"Error appending to Google Sheets: {e}")
            return {"status": "error", "message": str(e)}

    def _update_lead_column(self, profile_url: str, col_name: str, col_index: int, value: str):
        if not self._authenticate():
            return {"status": "error"}

        try:
            if self.spreadsheet_id:
                sheet = self.client.open_by_key(self.spreadsheet_id).sheet1
            else:
                sheet = self.client.open("Approved_LinkedIn_Outreach").sheet1
                
            # Ensure Header exists
            import string
            current_headers = sheet.row_values(1)
            
            # Pad missing headers if necessary
            headers_to_update = current_headers.copy()
            while len(headers_to_update) < col_index:
                headers_to_update.append("")
                
            if headers_to_update[col_index - 1] != col_name:
                headers_to_update[col_index - 1] = col_name
                col_letter = string.ascii_uppercase[col_index - 1]
                sheet.update(f'A1:{col_letter}1', [headers_to_update[:col_index]])

            # Find row
            urls = sheet.col_values(1)
            try:
                row_index = urls.index(profile_url) + 1
                sheet.update_cell(row_index, col_index, value)
                logging.info(f"Updated {col_name} on row {row_index} for {profile_url}")
                return {"status": "success"}
            except ValueError:
                logging.warning(f"Profile URL {profile_url} not found. Appending new row.")
                row_data = [""] * col_index
                row_data[0] = profile_url
                row_data[col_index - 1] = value
                sheet.append_row(row_data)
                return {"status": "success"}

        except Exception as e:
            logging.error(f"Error updating column {col_name} in Sheets: {e}")
            return {"status": "error", "message": str(e)}

    def append_linkedin_dm(self, profile_url: str, message: str):
        """Appends to the 4th column (followupMessage)"""
        return self._update_lead_column(profile_url, "followupMessage", 4, message)

    def append_cold_email(self, profile_url: str, message: str):
        """Appends to the 5th column (coldMail)"""
        return self._update_lead_column(profile_url, "coldMail", 5, message)

    def update_status(self, profile_url: str, status: str):
        """Updates the 6th column (status)"""
        return self._update_lead_column(profile_url, "status", 6, status)

    def clear_all_data(self):
        """
        Clears the entire sheet and resets the headers.
        """
        if not self._authenticate():
            return {"status": "error", "message": "Google Sheets Authentication failed"}
        
        try:
            if self.spreadsheet_id:
                sheet = self.client.open_by_key(self.spreadsheet_id).sheet1
            else:
                sheet = self.client.open("Approved_LinkedIn_Outreach").sheet1
            
            # Clear all contents
            sheet.clear()
            
            # Reset headers
            header_row = ["profileUrl", "firstName", "connectionNote"]
            sheet.insert_row(header_row, index=1)
            
            logging.info("Successfully cleared Google Sheet and reset headers.")
            return {"status": "success"}
        except Exception as e:
            logging.error(f"Error clearing Google Sheet: {e}")
            return {"status": "error", "message": str(e)}

