import os
import sys
import logging

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.app.services.google_sheets import GoogleSheetsService
from dotenv import load_dotenv

load_dotenv()

def test_sync():
    print("Testing Google Sheets Sync...")
    service = GoogleSheetsService()
    
    # Test column update (Status)
    # Using a dummy profile URL
    test_url = "https://www.linkedin.com/in/test-profile-123"
    
    print(f"Updating status for {test_url} to 'CONNECTED'...")
    result = service.update_status(test_url, "CONNECTED (TEST)")
    print(f"Result: {result}")
    
    if result.get("status") == "success":
        print("✅ Status sync successful!")
    else:
        print(f"❌ Status sync failed: {result.get('message')}")

if __name__ == "__main__":
    test_sync()
