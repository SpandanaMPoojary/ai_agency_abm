import os
from serpapi import GoogleSearch
import requests

class EnrichmentService:
    """Service to enrich leads with LinkedIn URLs and email addresses."""

    def __init__(self):
        self.serpapi_key = os.getenv('SERPAPI_KEY')
        self.hunter_key = os.getenv('HUNTER_API_KEY')
        
    def get_linkedin_url(self, name: str) -> str:
        """Find LinkedIn profile URL using Google Search via SerpAPI."""
        if not self.serpapi_key:
            raise ValueError("SERPAPI_KEY not set in environment.")
            
        params = {
            "q": f"site:linkedin.com/in/ {name}",
            "api_key": self.serpapi_key,
            "engine": "google"
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        
        organic_results = results.get("organic_results", [])
        if organic_results:
            return organic_results[0].get("link", "")
        return ""

    def get_professional_email(self, domain: str, first_name: str, last_name: str) -> dict:
        """Find professional email using Hunter.io."""
        if not self.hunter_key:
            raise ValueError("HUNTER_API_KEY not set in environment.")
            
        url = "https://api.hunter.io/v2/email-finder"
        params = {
            "domain": domain,
            "first_name": first_name,
            "last_name": last_name,
            "api_key": self.hunter_key
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json().get("data", {})
        return {"error": response.text}
