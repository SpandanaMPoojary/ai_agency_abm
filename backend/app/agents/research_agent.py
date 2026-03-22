import json
from backend.app.services.llm_client import LLMClient
from backend.app.services.research_service import ResearchService

class ResearchAgent:
    """Agent for identifying target accounts and researching leads"""

    def __init__(self):
        self.llm_client = LLMClient()
        self.research_service = ResearchService()

    def identify_target_accounts(self, icp_description, limit=5, platform="linkedin"):
        """
        Identify target accounts based on ICP
        """
        # 1. Generate search queries based on ICP
        query_prompt = f"""
        Based on the following Ideal Customer Profile (ICP), generate 3 specific Google search queries to find companies that match this profile.
        Ensure these queries are specifically targeting {platform} domains (e.g., site:linkedin.com/company or site:twitter.com).
        ICP: {icp_description}
        
        Format the output as a JSON list of strings.
        """
        queries_raw_obj = self.llm_client.generate(query_prompt)
        queries_raw = queries_raw_obj.text
        try:
            # Simple extraction of JSON list
            start = queries_raw.find('[')
            end = queries_raw.rfind(']') + 1
            queries = json.loads(queries_raw[start:end])
        except:
            queries = [f"{icp_description} {platform} companies"]

        # 2. Search for companies
        all_accounts = []
        for query in queries:
            results = self.research_service.search_companies(query)
            for res in results:
                all_accounts.append({
                    "name": res.get("title"),
                    "link": res.get("link"),
                    "snippet": res.get("snippet")
                })
                if len(all_accounts) >= limit:
                    return all_accounts[:limit]
        
        return all_accounts[:limit]

    def research_account_details(self, account_name, domain):
        """
        Research LinkedIn pages and decision makers
        """
        # This would normally trigger Phantombuster
        # For now, we simulate finding a decision maker and LinkedIn page
        linkedin_query = f"{account_name} LinkedIn company page"
        results = self.research_service.search_companies(linkedin_query)
        company_linkedin = results[0].get("link") if results else "Not found"

        # Find key decision maker (simulated)
        dm_query = f"{account_name} CEO OR 'Head of Sales' LinkedIn"
        dm_results = self.research_service.search_companies(dm_query)
        dm_link = dm_results[0].get("link") if dm_results else "Not found"
        dm_name = dm_results[0].get("title").split("-")[0].strip() if dm_results else "Unknown"

        return {
            "company_linkedin": company_linkedin,
            "decision_maker_name": dm_name,
            "decision_maker_linkedin": dm_link
        }

    def generate_personalization_hooks(self, account_name, snippet):
        """
        Generate hooks based on news/pain points
        """
        prompt = f"""
        Analyze the following information about the company '{account_name}':
        Info: {snippet}
        
        Generate 3 personalization hooks for an outreach email. These hooks should mention a potential pain point or recent context found in the snippet.
        """
        hooks_obj = self.llm_client.generate(prompt)
        return hooks_obj.text

    def execute_full_research(self, icp_description, limit=5, platform="linkedin"):
        """
        Execute the full research workflow
        """
        accounts = self.identify_target_accounts(icp_description, limit=limit, platform=platform)
        results = []
        
        for acc in accounts:
            # Extract domain from link if possible
            link = acc.get("link", "")
            domain = link.split("//")[-1].split("/")[0] if "://" in link else "unknown.com"
            details = self.research_account_details(acc['name'], domain)
            hooks = self.generate_personalization_hooks(acc['name'], acc['snippet'])
            
            results.append({
                "account": acc['name'],
                "website": link,
                "linkedin": details['company_linkedin'],
                "decision_maker": details['decision_maker_name'],
                "dm_linkedin": details['decision_maker_linkedin'],
                "personalization_hooks": hooks
            })
            
        return results
