import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

def view_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_path = "service_account.json"
    spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")
    
    try:
        credentials = Credentials.from_service_account_file(creds_path, scopes=scopes)
        client = gspread.authorize(credentials)
        sheet = client.open_by_key(spreadsheet_id).sheet1
        
        values = sheet.get_all_values()
        print(f"--- Sheet Content ({len(values)} rows) ---")
        for i, row in enumerate(values):
            print(f"Row {i+1}: {row}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    view_sheet()
