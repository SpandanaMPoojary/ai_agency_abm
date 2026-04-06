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
        System Role: You are a networking assistant. Write a LinkedIn connection message that is under 200 characters.
        The message should sound like a human peer in the same industry.

        CRITICAL RULES:
        1. NO 'I would like to add you to my professional network.'
        2. NO 'I am a [Job Title] looking to...'
        3. FORMAT: Start with a specific observation about their profile. End with a light, non-sales question.
        4. LENGTH: Must be STRICTLY under 200 characters.
        5. NO LINKS: Do NOT include any URLs or placeholders in this initial note.

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

    def generate_followups(self, account_data, icp, value_prop, connection_note=None):
        """
        Generate follow-up messages (LinkedIn DM and Email) after connection.
        Follows strict ANTI-SPAM rules and casual founder persona.
        """
        prompt = f"""
         System Role: You are a developer/founder sending a casual, 1-to-1 LinkedIn DM to a new connection.
        Tone: Casual, lowercase-leaning, "Text/Phone grammar". Avoid capital letters at the start of every sentence to feel more like a quick message.
        
        ANTI-SPAM & HUMANE RULES:
        1. NO "Thanks for connecting", "Happy to be in your network", or bot-like filler.
        2. FORBIDDEN PHRASES: "curious if it helps or if I'm overthinking it?", "let me know your thoughts", "open to a call".
        3. NO CORPORATE JARGON: Avoid "Streamline", "Efficiency", "Expertise", "Benefit", "Organization".
        4. NO ASKING FOR A CALL: Just drop the link as a resource they can check if/when they're bored.

        CRITICAL LINK RULES:
        1. MANDATORY PLACEHOLDER: You MUST include the exact placeholder string {{{{tracking_link}}}} in BOTH the LinkedIn DM and the Email body. 
        2. NO SAMPLE LINKS: Do NOT use any URLs like "example.com". ONLY use the placeholder {{{{tracking_link}}}}.

        Message Structure (LinkedIn DM):
        - STRICTLY 1-2 short sentences.
        - Style: Should look like a message from a dev who just thought of something relevant to the receiver's role.
        - Sentence 1: A casual mention matching their industry or role.
        - Sentence 2: Drop the {{{{tracking_link}}}} placeholder as a "here's that thing" or "made this for [industry]" reference.
        
        Message Structure (Email):
        - MUST include a "Subject:" line at the very top.
        - Subject should be lowercase and casual (e.g., "re: [industry] stuff" or "dashboard for [company]").
        - Body: Short, punchy, and lowercase-leaning.
        - Weave the {{{{tracking_link}}}} placeholder naturally into the body.


        Target Context:
        Lead/Account: {account_data}
        Target ICP: {icp}
        Agency Value Prop: {value_prop}

        Response Format:
        Return ONLY a raw JSON object with these keys: "step_2_linkedin_dm", "step_3_email".
        CRITICAL: The values for both keys MUST be plain strings. Do NOT return nested JSON objects or extra keys for Subject/Body.
        No preamble, no markdown formatting.
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
