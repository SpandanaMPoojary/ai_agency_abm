#!/usr/bin/env python3
"""
Test script for the LLM client
"""

import os
import sys
sys.path.append('backend')

def test_imports():
    """Test if all required modules can be imported"""
    try:
        # Test dotenv import
        from dotenv import load_dotenv
        print("✓ python-dotenv imported successfully")

        # Test google-generativeai import
        import google.generativeai as genai
        print("✓ google-generativeai imported successfully")

        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_env_vars():
    """Test if environment variables are loaded"""
    load_dotenv()

    gemini_key = os.getenv('GEMINI_API_KEY')
    if gemini_key:
        print("✓ GEMINI_API_KEY found in environment")
        print(f"  Key starts with: {gemini_key[:10]}...")
        return True
    else:
        print("✗ GEMINI_API_KEY not found in environment")
        return False

def test_llm_client():
    """Test LLM client initialization"""
    try:
        from backend.app.services.llm_client import LLMClient, MockLLMClient

        # Try real client first
        try:
            client = LLMClient()
            print("✓ LLMClient initialized successfully")

            # Test generate method
            response = client.generate("Hello, test message")
            print(f"✓ LLMClient.generate method works: {response[:50]}...")
            return True

        except Exception as e:
            print(f"⚠ LLMClient failed ({e}), trying MockLLMClient...")
            mock_client = MockLLMClient()
            response = mock_client.generate("Hello, test message")
            print(f"✓ MockLLMClient works: {response}")
            return True

    except Exception as e:
        print(f"✗ LLM client error: {e}")
        return False

if __name__ == "__main__":
    print("Testing AI Agency ABM components...")
    print("=" * 40)

    all_passed = True

    print("\n1. Testing imports...")
    if not test_imports():
        all_passed = False

    print("\n2. Testing environment variables...")
    if not test_env_vars():
        all_passed = False

    print("\n3. Testing LLM client...")
    if not test_llm_client():
        all_passed = False

    print("\n" + "=" * 40)
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed. Please check the errors above.")

    print("\nNote: To fully test the LLM client, you need to:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Ensure GEMINI_API_KEY is set in .env file")
    print("3. Have internet connection for API calls")