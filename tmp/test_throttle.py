import sys
import os
from datetime import datetime, timedelta
import json

# Add project root to sys.path
sys.path.append(os.getcwd())

# Mock environment
os.environ["LIVE_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:" # To avoid DB connection issues if main.py imports it

# We need to mock the DB engine before importing main
import sqlmodel
from sqlmodel import create_engine
# The main.py uses DATABASE_URL at module level.

from backend.main import check_and_update_throttle, THROTTLE_FILE

def test():
    # Reset throttle file
    if os.path.exists(THROTTLE_FILE):
        os.remove(THROTTLE_FILE)
    
    print("Testing 1st launch...")
    allowed, msg = check_and_update_throttle(limit=2)
    print(f"Allowed: {allowed}, Msg: {msg}")
    
    print("Testing 2nd launch...")
    allowed, msg = check_and_update_throttle(limit=2)
    print(f"Allowed: {allowed}, Msg: {msg}")
    
    print("Testing 3rd launch (should be blocked)...")
    allowed, msg = check_and_update_throttle(limit=2)
    print(f"Allowed: {allowed}, Msg: {msg}")

    # Manually backdate one launch to 1.1 hours ago
    with open(THROTTLE_FILE, "r") as f:
        data = json.load(f)
    
    backdated = (datetime.utcnow() - timedelta(hours=1.1)).isoformat()
    data["launches"][0] = backdated
    
    with open(THROTTLE_FILE, "w") as f:
        json.dump(data, f)
        
    print("Testing 4th launch (after backdating 1st launch)...")
    allowed, msg = check_and_update_throttle(limit=2)
    print(f"Allowed: {allowed}, Msg: {msg}")

if __name__ == "__main__":
    test()
