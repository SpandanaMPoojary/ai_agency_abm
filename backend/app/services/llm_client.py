import os
import replicate
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    """Client for interacting with Replicate (Llama 3.3 70B)"""

    def __init__(self):
        """Initialize the Replicate client"""
        self.api_token = os.getenv('REPLICATE_API_KEY') or os.getenv('REPLICATE_API_TOKEN')
        if not self.api_token:
            raise ValueError("REPLICATE_API_KEY or REPLICATE_API_TOKEN is not set")
        
        # Set for the library
        os.environ["REPLICATE_API_TOKEN"] = self.api_token
        self.model_name = "meta/meta-llama-3-70b-instruct"

    def generate(self, prompt):
        """
        Generate a response from the Llama model via Replicate
        """
        try:
            # Using the prompt-based generation for Llama
            output = replicate.run(
                self.model_name,
                input={
                    "prompt": prompt,
                    "max_new_tokens": 1024,
                    "temperature": 0.7,
                    "top_p": 0.9,
                }
            )
            
            # Replicate output for Llama is typically a generator of strings
            full_text = "".join(output)
            
            class LLMResponse:
                def __init__(self, text):
                    self.text = text
            
            return LLMResponse(full_text)
            
        except Exception as e:
            raise Exception(f"Error generating response from Replicate: {str(e)}")

class MockLLMClient:
    """Mock version of LLMClient for testing"""
    def __init__(self):
        self.responses = ["Mock Llama response 1", "Mock Llama response 2"]
        self.index = 0

    def generate(self, prompt):
        response_text = self.responses[self.index % len(self.responses)]
        self.index += 1
        class MockResponse:
            def __init__(self, text):
                self.text = text
        return MockResponse(f"[MOCK] {response_text}")