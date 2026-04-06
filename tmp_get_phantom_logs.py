import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("PHANTOMBUSTER_API_KEY")
PHANTOM_ID = os.getenv("PHANTOM_AUTO_CONNECT_ID")

def get_logs():
    headers = {"X-Phantombuster-Key": API_KEY}
    
    # 1. Get agent
    url = f"https://api.phantombuster.com/api/v2/agents/fetch?id={PHANTOM_ID}"
    res = requests.get(url, headers=headers)
    if not res.ok:
        print("Error fetching agent")
        return
    
    agent = res.json()
    container_id = agent.get("containerId")
    if not container_id:
        print("No container ID found")
        return

    # 2. Get console
    url = f"https://api.phantombuster.com/api/v2/containers/fetch-console?id={container_id}"
    res = requests.get(url, headers=headers)
    if res.ok:
        print("--- CONSOLE START ---")
        print(res.text)
        print("--- CONSOLE END ---")
    else:
        print(f"Error fetching console: {res.status_code}")

if __name__ == "__main__":
    get_logs()
