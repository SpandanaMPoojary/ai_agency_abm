import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("PHANTOMBUSTER_API_KEY")
PHANTOM_ID = os.getenv("PHANTOM_AUTO_CONNECT_ID")

def check_phantom():
    url = f"https://api.phantombuster.com/api/v2/agents/fetch-output?id={PHANTOM_ID}"
    headers = {"X-Phantombuster-Key": API_KEY}
    
    print(f"Checking Phantom output for {PHANTOM_ID}...")
    res = requests.get(url, headers=headers)
    
    if res.ok:
        data = res.json()
        print(json.dumps(data, indent=2))
    else:
        print(f"API Error: {res.status_code} {res.text}")

if __name__ == "__main__":
    check_phantom()
