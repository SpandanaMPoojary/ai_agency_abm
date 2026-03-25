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
        self.message_sender_phantom_id = os.getenv("PHANTOM_MESSAGE_SENDER_ID")
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
            # Trigger the Phantom without overrides so it reads precisely the user's config
            payload = {
                "id": self.phantom_id
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
            # 1. Fetch the agent's latest metadata to get the containerId
            agent_url = f"https://api.phantombuster.com/api/v2/agents/fetch-output?id={self.connections_phantom_id}"
            headers = {"X-Phantombuster-Key": self.api_key}
            
            response = requests.get(agent_url, headers=headers)
            response.raise_for_status()
            
            agent_data = response.json()
            container_id = agent_data.get("containerId")
            
            if not container_id:
                logging.error(f"[LIVE] No containerId found in agent output: {agent_data}")
                return {"status": "error", "message": "Phantom hasn't run successfully yet (No container ID)."}

            # 2. Fetch the actual result object from the container
            container_url = f"https://api.phantombuster.com/api/v2/containers/fetch-result-object?id={container_id}"
            res_response = requests.get(container_url, headers=headers)
            res_response.raise_for_status()
            
            res_data = res_response.json()
            result_obj = res_data.get("resultObject")
            
            connections = []
            if isinstance(result_obj, str):
                import json
                try:
                    connections = json.loads(result_obj)
                except Exception as e:
                    logging.error(f"[LIVE] JSON parse failed for resultObject: {e}")
            elif isinstance(result_obj, list):
                connections = result_obj
            
            if not isinstance(connections, list):
                logging.warning(f"[PB] Connections object is not a list: {type(connections)}")
                connections = []

            # 3. Search for the profile_url in the connections list
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

    def trigger_message_sender(self, profile_url: str, message: str):
        """
        Triggers the LinkedIn Message Sender Phantom.
        """
        if not self.live_mode:
            logging.info(f"[SANDBOX] Simulating Followup Message to {profile_url}")
            return {"status": "success", "container_id": "sandbox_12345"}
            
        if not self.api_key or not self.message_sender_phantom_id:
            logging.error("[LIVE] Missing API Key or Message Sender Phantom ID")
            return {"status": "error", "message": "Missing Phantombuster configuration for Message Sender"}
            
        try:
            url = "https://api.phantombuster.com/api/v2/agents/launch"
            headers = {
                "X-Phantombuster-Key": self.api_key,
                "Content-Type": "application/json"
            }
            
            # Since the user has configured the Phantom to read from the Google Sheet,
            # we just need to trigger the launch without any overrides.
            payload = {
                "id": self.message_sender_phantom_id
            }
            
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            return {"status": "success", "container_id": data.get("containerId")}
        except Exception as e:
            logging.error(f"[LIVE] Failed to trigger Message Sender Phantom: {str(e)}")
            return {"status": "error", "message": str(e)}

