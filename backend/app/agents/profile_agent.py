import json
from backend.app.services.llm_client import LLMClient


class ProfileAgent:
    """Agent for auditing and improving company profiles"""

    def __init__(self):
        """Initialize the ProfileAgent with LLMClient"""
        self.llm_client = LLMClient()

    def audit_profile(self, profile_data):
        """
        Audit a company profile and suggest improvements

        Args:
            profile_data (dict): Profile data containing:
                - company_name (str): Company name
                - headline (str): Profile headline
                - summary (str): Company summary
                - experience (str): Relevant experience/achievements
                - current_cta (str): Current call to action

        Returns:
            dict: Audit results with suggestions for:
                - headline_suggestions
                - summary_suggestions
                - experience_suggestions
                - cta_suggestions
                - overall_score
                - priority_improvements
        """
        prompt = f"""
        You are an expert in B2B profile optimization and positioning.
        
        Analyze the following company profile and provide specific, actionable improvements:
        
        Company Name: {profile_data.get('company_name', 'N/A')}
        Current Headline: {profile_data.get('headline', 'N/A')}
        Current Summary: {profile_data.get('summary', 'N/A')}
        Current Experience/Achievements: {profile_data.get('experience', 'N/A')}
        Current CTA: {profile_data.get('current_cta', 'N/A')}
        
        Please provide:
        1. 3-5 specific suggestions for improving the headline
        2. 3-5 suggestions for strengthening the summary
        3. 2-3 suggestions for highlighting relevant experience
        4. 2-3 suggestions for a more compelling CTA
        5. An overall profile quality score (1-10)
        6. Top 3 priority improvements to make immediately
        
        Format your response as a clear, structured list with each section clearly labeled.
        """

        response_obj = self.llm_client.generate(prompt)
        response = response_obj.text

        return {
            "audit_response": response,
            "profile_audited": profile_data.get('company_name', 'Unknown'),
            "suggestions": self._parse_suggestions(response)
        }

    def generate_positioning(self, industry, icp, competitors):
        """
        Generate a positioning statement and tagline for a company

        Args:
            industry (str): Industry/vertical the company operates in
            icp (str): Ideal Customer Profile description
            competitors (list): List of competitor names or descriptions

        Returns:
            dict: Generated positioning with:
                - positioning_statement
                - tagline
                - brand_voice_characteristics
                - key_differentiators
                - elevator_pitch
        """
        competitors_text = ", ".join(competitors) if isinstance(competitors, list) else competitors

        prompt = f"""
        You are an expert brand strategist specializing in B2B positioning.
        
        Create a comprehensive positioning strategy for a company with these characteristics:
        
        Industry: {industry}
        Ideal Customer Profile (ICP): {icp}
        Main Competitors: {competitors_text}
        
        Please generate:
        1. A compelling 2-3 sentence positioning statement that clearly differentiates from competitors
        2. A memorable tagline (5-8 words) that captures the brand essence
        3. Key brand voice characteristics (3-5 traits that define how we communicate)
        4. Top 3 key differentiators that set us apart
        5. A 30-second elevator pitch for the ICP
        
        Ensure the positioning:
        - Speaks directly to the ICP's pain points
        - Clearly differentiates from competitors
        - Is authentic and maintainable as a brand voice
        - Focuses on value delivered, not features
        
        Format your response with clear sections for each element.
        """

        response_obj = self.llm_client.generate(prompt)
        response = response_obj.text

        return {
            "positioning_response": response,
            "industry": industry,
            "icp": icp,
            "competitors_analyzed": competitors if isinstance(competitors, list) else [competitors],
            "positioning_elements": self._parse_positioning(response)
        }

    def _parse_suggestions(self, response):
        """
        Parse audit suggestions from LLM response

        Args:
            response (str): Raw response from LLM

        Returns:
            dict: Parsed suggestions organized by category
        """
        from typing import Dict, List
        parsed: Dict[str, List[str]] = {
            "headline": [],
            "summary": [],
            "experience": [],
            "cta": [],
            "priority_improvements": []
        }

        # Simple parsing - in production this would be more sophisticated
        lines = response.split('\n')
        current_section = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if 'headline' in line.lower():
                current_section = 'headline'
            elif 'summary' in line.lower():
                current_section = 'summary'
            elif 'experience' in line.lower():
                current_section = 'experience'
            elif 'cta' in line.lower():
                current_section = 'cta'
            elif 'priority' in line.lower():
                current_section = 'priority_improvements'
            elif current_section and line.startswith(('-', '•', '*', '1', '2', '3', '4', '5')):
                if current_section in parsed:
                    parsed[current_section].append(line.lstrip('-•* 0123456789.').strip())

        return parsed

    def _parse_positioning(self, response):
        """
        Parse positioning elements from LLM response

        Args:
            response (str): Raw response from LLM

        Returns:
            dict: Parsed positioning elements
        """
        from typing import Dict, Any
        parsed: Dict[str, Any] = {
            "positioning_statement": "",
            "tagline": "",
            "brand_voice": [],
            "differentiators": [],
            "elevator_pitch": ""
        }

        lines = response.split('\n')
        current_section = None

        for i, line in enumerate(lines):
            line_lower = line.lower()

            if 'positioning statement' in line_lower:
                current_section = 'positioning_statement'
                # Try to get the next non-empty line
                if i + 1 < len(lines):
                    parsed['positioning_statement'] = lines[i + 1].strip()
            elif 'tagline' in line_lower:
                current_section = 'tagline'
                if i + 1 < len(lines):
                    parsed['tagline'] = lines[i + 1].strip()
            elif 'brand voice' in line_lower or 'brand characteristics' in line_lower:
                current_section = 'brand_voice'
            elif 'differentiator' in line_lower:
                current_section = 'differentiators'
            elif 'elevator pitch' in line_lower:
                current_section = 'elevator_pitch'
                if i + 1 < len(lines):
                    parsed['elevator_pitch'] = lines[i + 1].strip()
            elif current_section and line.strip().startswith(('-', '•', '*', '1', '2', '3')):
                item = line.lstrip('-•* 0123456789.').strip()
                if current_section == 'brand_voice':
                    parsed['brand_voice'].append(item)
                elif current_section == 'differentiators':
                    parsed['differentiators'].append(item)

        return parsed