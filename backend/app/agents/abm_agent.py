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
        System Role: You are an expert ABM Strategist for a B2B AI Agency. 
        Your goal is to generate a highly personalized 3-step outreach sequence for a target lead.

        Target Context:
        Lead/Account: {account_data}
        Target ICP: {icp}
        Agency Value Prop: {value_prop}

        Output Requirements:
        1. Return exactly three steps:
           - step_1_linkedin: Short, punchy connection note (<300 chars).
           - step_2_email: Professional cold email with a compelling subject line.
           - step_3_followup: Gentle LinkedIn follow-up message for 3 days later.
        
        2. Tracking Link: Every message MUST include this exact placeholder: "[[TRACKING_LINK]]".
           Do NOT replace it with a real link.

        3. Response Format: You MUST return ONLY a raw JSON object with these keys: 
           "step_1_linkedin", "step_2_email", "step_3_followup".
           No preamble, no markdown formatting blocks, just the raw JSON.
        """
        
        response_obj = self.llm_client.generate(prompt)
        response_raw = response_obj.text
        
        try:
            # Clean up potential markdown formatting if Llama adds it
            cleaned_raw = response_raw.strip()
            if cleaned_raw.startswith("```json"):
                cleaned_raw = cleaned_raw.replace("```json", "", 1)
            if cleaned_raw.endswith("```"):
                cleaned_raw = cleaned_raw.rsplit("```", 1)[0]
            cleaned_raw = cleaned_raw.strip()

            sequence = json.loads(cleaned_raw)
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
