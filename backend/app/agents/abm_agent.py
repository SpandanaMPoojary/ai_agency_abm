import json
from backend.app.services.llm_client import LLMClient

class ABMAgent:
    """Agent for orchestrating high-conversion ABM outreach sequences"""

    def __init__(self):
        self.llm_client = LLMClient()

    def generate_outreach_sequence(self, account_data, icp, value_prop):
        """
        Generate a 3-step outreach sequence (LinkedIn, Email, Follow-up)
        
        Args:
            account_data (str/dict): Information about the target account/lead
            icp (str): Target Ideal Customer Profile
            value_prop (str): Agency's core value proposition
            
        Returns:
            list: A list of JSON objects containing channel, message, cta, and status
        """
        prompt = f"""
        System Role: You are the ABMAgent, an expert in Account-Based Marketing (ABM) for a B2B AI Agency. 
        Your goal is to orchestrate a high-conversion, multi-touch outreach sequence.

        Input Data:
        Target Account: {account_data}
        Target ICP: {icp}
        Core Content: {value_prop}

        Instructions:
        1. Generate a 3-Step Sequence: Create a coordinated outreach flow using three distinct channels: LinkedIn DM, Email, and a Follow-up.
        2. Personalization: Ensure each message is personalized to the account's specific industry and pain points.
        3. Lead Scoring Logic: Define the trigger for the next step (e.g., "If they click the link, increase lead score and notify CRM").
        4. Call to Action (CTA): Include a clear CTA in each message, such as booking a discovery call.
        5. Output Format: You MUST output the result as a raw JSON array of objects with the following keys: channel, message, cta, status. 
           In 'status', include the lead scoring/trigger logic for that step.

        Ensure the response is ONLY the raw JSON array.
        """

        response_obj = self.llm_client.generate(prompt)
        response_raw = response_obj.text
        
        try:
            # Attempt to parse the JSON response
            start = response_raw.find('[')
            end = response_raw.rfind(']') + 1
            sequence = json.loads(response_raw[start:end])
            return sequence
        except Exception as e:
            # Fallback or manual extraction if LLM didn't format perfectly
            return {
                "error": "Failed to parse JSON from LLM",
                "raw_response": response_raw
            }

if __name__ == "__main__":
    # Example usage for testing
    agent = ABMAgent()
    test_account = "John Doe, Founder at AI Startup"
    test_icp = "Cybersecurity Audit Firms"
    test_value_prop = "Automating compliance audits with LLMs"
    
    sequence = agent.generate_outreach_sequence(test_account, test_icp, test_value_prop)
    print(json.dumps(sequence, indent=2))
