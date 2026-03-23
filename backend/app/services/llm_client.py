import os
# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Use os.environ directly

class LLMClient:
    """Client for interacting with Google Gemini (gemini-1.5-flash)"""

    def __init__(self):
        """Initialize the Gemini client with API key"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")

        try:
            from google import genai
            self.client = genai.Client(api_key=api_key)
            self.model_name = 'gemini-1.5-flash'
            self.api_available = True
        except ImportError:
            print("Warning: google-genai not installed. Using mock responses.")
            self.api_available = False

    def generate(self, prompt):
        """
        Generate a response from the Gemini model

        Args:
            prompt (str): The prompt to send to the model

        Returns:
            object: The response object from the model
        """
        if self.api_available:
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                return response
            except Exception as e:
                raise Exception(f"Error generating response from Gemini: {str(e)}")
        else:
            # Mock response object for testing when package is not available
            class MockResponse:
                def __init__(self, text):
                    self.text = text
            return MockResponse(f"[MOCK RESPONSE] This is a simulated response to: '{prompt[:50]}...'")

class MockLLMClient:
    """Mock version of LLMClient for testing without API dependencies"""

    def __init__(self):
        """Initialize mock client"""
        self.responses = [
            "Thank you for your inquiry. I'd be happy to help you with that.",
            "Based on the information provided, here are some recommendations...",
            "I understand your requirements. Let me provide a detailed response.",
            "This is an excellent question. Here's what I can tell you...",
            "I'd recommend considering the following approach for your project."
        ]
        self.index = 0

    def generate(self, prompt):
        """Generate a mock response"""
        response_text = self.responses[self.index % len(self.responses)]
        self.index += 1
        class MockResponse:
            def __init__(self, text):
                self.text = text
        return MockResponse(f"[MOCK] {response_text}")