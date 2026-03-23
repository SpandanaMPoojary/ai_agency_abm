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
        1. Generate a 3-Step Sequence:
           - step_1_linkedin: A short, punchy connection note (STRICTLY < 300 characters).
           - step_2_email: A professional cold email with a clear subject line and body.
           - step_3_followup: A gentle LinkedIn follow-up message to be sent 3 days later.
        2. Personalization: Use the target account's industry and pain points to make each message feel 1-to-1.
        3. Tracking Link: You MUST include the placeholder "[[TRACKING_LINK]]" in EVERY message.
           Example: "Check this out: [[TRACKING_LINK]]"
        4. Output Format: You MUST output the result as a raw JSON object (NOT an array) with exactly these keys:
           "step_1_linkedin", "step_2_email", "step_3_followup".

        Ensure the response is ONLY the raw JSON object.
        """
        
        response_obj = self.llm_client.generate(prompt)
        response_raw = response_obj.text
        
        try:
            # Attempt to parse the JSON response
            start = response_raw.find('{')
            end = response_raw.rfind('}') + 1
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
