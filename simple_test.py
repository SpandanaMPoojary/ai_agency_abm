#!/usr/bin/env python3
"""
Simple test to verify basic functionality
"""

print("Testing AI Agency ABM Components")
print("=" * 40)

# Test 1: Python environment
import sys
print(f"✓ Python version: {sys.version}")

# Test 2: Environment variables
import os
# Try to load dotenv if available, otherwise use os.environ
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ python-dotenv available")
except ImportError:
    print("⚠ python-dotenv not available, using os.environ")

gemini_key = os.getenv('GEMINI_API_KEY')
if gemini_key:
    print("✓ GEMINI_API_KEY found")
else:
    print("⚠ GEMINI_API_KEY not found")

# Test 3: Database connection
try:
    import psycopg2
    print("✓ psycopg2 available")

    # Try to connect to database
    try:
        conn = psycopg2.connect(
            host="localhost",
            port="5432",
            database="ai_agency_db",
            user="postgres",
            password="myp@ss123"
        )
        conn.close()
        print("✓ Database connection successful")
    except Exception as e:
        print(f"⚠ Database connection failed: {e}")

except ImportError:
    print("⚠ psycopg2 not available")

# Test 4: LLM Client
try:
    from backend.app.services.llm_client import LLMClient, MockLLMClient

    try:
        client = LLMClient()
        response = client.generate("Test prompt")
        print(f"✓ LLMClient works: {response[:30]}...")
    except Exception as e:
        print(f"⚠ LLMClient failed, using mock: {e}")
        mock_client = MockLLMClient()
        response = mock_client.generate("Test prompt")
        print(f"✓ MockLLMClient works: {response}")

except ImportError as e:
    print(f"⚠ LLM client import failed: {e}")

print("\n" + "=" * 40)
print("Test completed!")
print("\nTo fix SSL issues:")
print("1. Try: pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt")
print("2. Or use: conda install psycopg2 python-dotenv google-generativeai")
print("3. Or update your Python environment")