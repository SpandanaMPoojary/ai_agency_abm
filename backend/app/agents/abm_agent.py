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
        Your goal is to generate a highly personalized LinkedIn Connection Note for a target lead.

        Strict Constraints:
        1. CONTENT: Only generate a Connection Note. No follow-ups or emails.
        2. LENGTH: The note must be STRICTLY under 180 characters total. Be extremely concise.
        3. NO LINKS: Do NOT include any URLs or the [[TRACKING_LINK]] placeholder in this Connection Note. Focus on a warm, professional connection.

        Target Context:
        Lead/Account: {account_data}
        Target ICP: {icp}
        Agency Value Prop: {value_prop}

        Output Requirement:
        Return ONLY a raw JSON object with this key: "step_1_connection_note".
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

    def generate_followups(self, account_data, icp, value_prop):
        """
        Generate follow-up messages (LinkedIn DM and Email) after connection
        """
        prompt = f"""
        System Role: You are an expert ABM Strategist for a B2B AI Agency. 
        Your goal is to generate conditional follow-up messages for a lead who has just ACCEPTED your connection request.

        Target Context:
        Lead/Account: {account_data}
        Target ICP: {icp}
        Agency Value Prop: {value_prop}

        Output Requirements:
        1. step_2_linkedin_dm: A personalized LinkedIn message sent immediately after connection. 
           Mention our specific value prop for their business.
        2. step_3_email: A professional follow-up email sent 2 days later if no reply.
        3. TRACKING: Both messages MUST include the placeholder "[[TRACKING_LINK]]".

        Response Format:
        Return ONLY a raw JSON object with these keys: "step_2_linkedin_dm", "step_3_email".
        No preamble, no markdown.
        """
        
        response_obj = self.llm_client.generate(prompt)
        response_raw = response_obj.text
        
        try:
            cleaned_raw = response_raw.strip()
            if cleaned_raw.startswith("```json"):
                cleaned_raw = cleaned_raw.replace("```json", "", 1)
            if cleaned_raw.endswith("```"):
                cleaned_raw = cleaned_raw.rsplit("```", 1)[0]
            cleaned_raw = cleaned_raw.strip()

            return json.loads(cleaned_raw)
        except Exception as e:
            return {"error": "Failed to parse followups", "raw": response_raw}

if __name__ == "__main__":
    # Example usage for testing
    agent = ABMAgent()
    test_account = "John Doe, Founder at AI Startup"
    test_icp = "Cybersecurity Audit Firms"
    test_value_prop = "Automating compliance audits with LLMs"
    
    sequence = agent.generate_outreach_sequence(test_account, test_icp, test_value_prop)
    print(json.dumps(sequence, indent=2))
