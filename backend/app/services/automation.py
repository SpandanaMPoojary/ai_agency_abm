import os
import requests

class AutomationService:
    """Service to orchestrate outreach workflow via Phantombuster."""
    
    def __init__(self):
        self.pb_key = os.getenv('PHANTOMBUSTER_API_KEY')
        
    def trigger_linkedin_outreach(self, agent_id: str, profile_url: str, message: str) -> dict:
        """Trigger a Phantombuster LinkedIn Outreach Phantom."""
        if not self.pb_key:
            raise ValueError("PHANTOMBUSTER_API_KEY not set in environment.")
            
        url = f"https://api.phantombuster.com/api/v2/agents/launch"
        headers = {
            "x-phantombuster-key": self.pb_key,
            "Content-Type": "application/json" # optional but good practice
        }
        
        # The argument payload depends entirely on how the Phantom is configured.
        payload = {
            "id": agent_id,
            "argument": {
                "profileUrl": profile_url,
                "message": message
            }
        }
        
        response = requests.post(url, headers=headers, json=payload)
        return response.json()
