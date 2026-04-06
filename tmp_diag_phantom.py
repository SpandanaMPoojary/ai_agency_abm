import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("PHANTOM_BUSTER_API_KEY") # Check if it's the right env name
if not API_KEY:
    API_KEY = os.getenv("PHANTOMBUSTER_API_KEY")
PHANTOM_ID = os.getenv("PHANTOM_AUTO_CONNECT_ID")

def diag():
    headers = {"X-Phantombuster-Key": API_KEY}
    
    # 1. Fetch agent info
    agent_url = f"https://api.phantombuster.com/api/v2/agents/fetch?id={PHANTOM_ID}"
    print(f"--- Fetching Agent Info: {PHANTOM_ID} ---")
    res = requests.get(agent_url, headers=headers)
    if res.ok:
        print(json.dumps(res.json(), indent=2))
        container_id = res.json().get("containerId")
    else:
        print(f"Error fetching agent: {res.status_code} {res.text}")
        return

    # 2. Fetch latest output console
    output_url = f"https://api.phantombuster.com/api/v2/agents/fetch-output?id={PHANTOM_ID}"
    print("\n--- Fetching Agent Console Output ---")
    res = requests.get(output_url, headers=headers)
    if res.ok:
        # Console output is often a string in 'output' or similar
        print(res.text[:1000]) # Print first 1000 chars
    else:
        print(f"Error fetching output: {res.status_code} {res.text}")

    # 3. Fetch container result if exists
    if container_id:
        print(f"\n--- Fetching Container Result: {container_id} ---")
        container_url = f"https://api.phantombuster.com/api/v2/containers/fetch-result-object?id={container_id}"
        res = requests.get(container_url, headers=headers)
        if res.ok:
            print(json.dumps(res.json(), indent=2))
        else:
            print(f"Error fetching container result: {res.status_code} {res.text}")

if __name__ == "__main__":
    diag()
