import os
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Setup logging
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    filename='logs/outreach.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class AutomationService:
    def __init__(self):
        self.api_key = os.getenv("PHANTOMBUSTER_API_KEY")
        self.phantom_id = os.getenv("LINKEDIN_MESSAGE_PHANTOM_ID")
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
            url = f"https://api.phantombuster.com/api/v1/agent/{self.phantom_id}/launch"
            headers = {
                "X-Phantombuster-Key-1": self.api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "argument": {
                    "profileUrl": profile_url,
                    "message": message
                }
            }
            
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            logging.info(f"[LIVE] Successfully launched Phantom for {profile_url}. Response: {response.text}")
            return {"status": "success", "result": response.json()}
            
        except Exception as e:
            logging.error(f"[LIVE] Failed to trigger Phantom for {profile_url}: {str(e)}")
            return {"status": "error", "message": str(e)}
