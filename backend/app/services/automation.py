import os
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)

# Setup logging
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    filename='logs/outreach.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class AutomationService:
    def __init__(self):
        self.api_key = os.getenv("PHANTOMBUSTER_API_KEY")
        self.phantom_id = os.getenv("PHANTOM_AUTO_CONNECT_ID")
        self.connections_phantom_id = os.getenv("PHANTOM_CONNECTIONS_EXPORT_ID")
        self.test_email = os.getenv("TEST_EMAIL", "").strip().lower()
        self.live_mode = os.getenv("LIVE_MODE", "false").lower() == "true"

    def trigger_linkedin_outreach(self, profile_url: str, message: str, email: str = None):
        """
        Triggers a LinkedIn message via PhantomBuster.
        In Sandbox mode (or for TEST_EMAIL), it only logs the action.
        In Live mode, it calls the real API.
        """
        # Sandbox check (email based)
        processed_email = email.strip().lower() if email else ""
        is_sandbox_email = processed_email == self.test_email
        
        if not self.live_mode or is_sandbox_email:
            mode_str = "SANDBOX" if is_sandbox_email else "DEVELOPMENT (LIVE_MODE=false)"
            msg = f"FIRE COMMAND RECEIVED for {email or 'Unknown'} ({mode_str})"
            print(msg)
            logging.info(f"[{mode_str}] Would fire to {profile_url} with message: {message[:50]}...")
            return {"status": "success", "mode": mode_str}

        # LIVE MODE
        logging.info(f"[LIVE] Attempting to fire Phantom {self.phantom_id} for {profile_url}")
        
        if not self.api_key or not self.phantom_id:
            logging.error("[LIVE] Missing API Key or Phantom ID")
            return {"status": "error", "message": "Missing Phantombuster configuration"}

        try:
            url = "https://api.phantombuster.com/api/v2/agents/launch"
            headers = {
                "X-Phantombuster-Key": self.api_key,
                "Content-Type": "application/json"
            }
            # Many LinkedIn Message phantoms use 'spreadsheetUrl' as the primary input key
            # even when passing a single profile URL.
            payload = {
                "id": self.phantom_id,
                "argument": {
                    "spreadsheetUrl": profile_url,
                    "message": message,
                    "numberOfSendsPerLaunch": 1
                }
            }
            
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            logging.info(f"[LIVE] Successfully launched Phantom {self.phantom_id} for {profile_url}. Response: {response.text}")
            return {"status": "success", "result": response.json()}
            
        except Exception as e:
            msg = f"Request Failed: {str(e)}"
            if 'response' in locals():
                msg += f" | Response: {response.text}"
            logging.error(f"[LIVE] Failed to trigger Phantom {self.phantom_id} for {profile_url}: {msg}")
            return {"status": "error", "message": msg}

    def check_linkedin_acceptance(self, profile_url: str):
        """
        Checks if a LinkedIn profile URL is in the recent connections list.
        Uses PHANTOM_CONNECTIONS_EXPORT_ID to fetch output.
        """
        if not self.live_mode:
            logging.info(f"[SANDBOX] Automated acceptance check for {profile_url} -> Simulated ACCEPTED")
            return {"status": "success", "accepted": True}

        if not self.api_key or not self.connections_phantom_id:
            logging.error("[LIVE] Missing API Key or Connections Phantom ID")
            return {"status": "error", "message": "Missing Phantombuster configuration for connections"}

        try:
            # 1. Fetch the output of the connections phantom (Standard Result Endpoint)
            # format=json-array is often the most reliable way to get the array directly
            url = f"https://api.phantombuster.com/api/v2/agents/fetch-output?id={self.connections_phantom_id}&format=json-array"
            headers = {"X-Phantombuster-Key": self.api_key}
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Phantombuster fetch-output?format=json-array returns a JSON list directly
            connections = response.json()
            
            if not isinstance(connections, list):
                # Fallback to checking for a 'result' key if it returned an object
                if isinstance(connections, dict) and "result" in connections:
                    connections = connections["result"] or []
                else:
                    logging.warning(f"[PB] Connections object is not a list: {type(connections)}")
                    connections = []

            # 2. Search for the profile_url in the connections list
            target_profile = profile_url.lower().rstrip('/')
            
            def get_id(url):
                return url.split('/in/')[-1].split('/')[0] if '/in/' in url else url

            target_id = get_id(target_profile)
            logging.info(f"[DEBUG] Checking acceptance for {target_profile} (ID: {target_id}). Found {len(connections)} connections.")

            for conn in connections:
                # Phantombuster Export usually has 'profileUrl' or 'url'
                conn_url = (conn.get("profileUrl") or conn.get("url") or "").lower().rstrip('/')
                if not conn_url: continue
                
                if conn_url == target_profile or get_id(conn_url) == target_id:
                    logging.info(f"[LIVE] Connection accepted confirmed for {profile_url}")
                    return {"status": "success", "accepted": True}
            
            logging.info(f"[LIVE] Connection NOT yet found for {profile_url}. Checked {len(connections)} items.")
            return {"status": "success", "accepted": False}

        except Exception as e:
            logging.error(f"[LIVE] Failed to fetch connections for {profile_url}: {str(e)}")
            return {"status": "error", "message": f"Fetch failed: {str(e)}"}
