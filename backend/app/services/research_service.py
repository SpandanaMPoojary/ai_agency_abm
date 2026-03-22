import os
import requests
from serpapi import GoogleSearch
from dotenv import load_dotenv

load_dotenv()

class ResearchService:
    """Service to handle external API integrations for research"""
    
    def __init__(self):
        self.serp_api_key = os.getenv("SERPAPI_KEY")
        self.hunter_api_key = os.getenv("HUNTER_API_KEY")
        self.phantombuster_api_key = os.getenv("PHANTOMBUSTER_API_KEY")
        self.clearbit_api_key = os.getenv("CLEARBIT_API_KEY")

    def search_companies(self, query):
        """Search for companies using SerpAPI"""
        if not self.serp_api_key:
            return {"error": "SerpAPI key not found"}
            
        params = {
            "q": query,
            "api_key": self.serp_api_key,
            "engine": "google"
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        return results.get("organic_results", [])

    def find_verified_email(self, domain, first_name, last_name):
        """Find verified email using Hunter.io"""
        if not self.hunter_api_key:
            return {"error": "Hunter.io API key not found"}
            
        url = f"https://api.hunter.io/v2/email-finder?domain={domain}&first_name={first_name}&last_name={last_name}&api_key={self.hunter_api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get("data", {})
        return {"error": "Hunter.io search failed"}

    def run_phantombuster_agent(self, agent_id, argument):
        """Trigger a Phantombuster agent"""
        if not self.phantombuster_api_key:
            return {"error": "Phantombuster API key not found"}
            
        url = f"https://api.phantombuster.com/api/v2/agents/launch"
        headers = {"x-phantombuster-key": self.phantombuster_api_key}
        payload = {"id": agent_id, "argument": argument}
        response = requests.post(url, headers=headers, json=payload)
        return response.json()
