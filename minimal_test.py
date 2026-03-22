#!/usr/bin/env python3
"""
Minimal test without external dependencies
"""

print("AI Agency ABM - Basic Test")
print("=" * 30)

# Test 1: Python
import sys
print(f"✓ Python: {sys.version.split()[0]}")

# Test 2: Environment variables
import os
gemini_key = os.getenv('GEMINI_API_KEY')
if gemini_key:
    print("✓ GEMINI_API_KEY: Found")
else:
    print("⚠ GEMINI_API_KEY: Not found")

# Test 3: File structure
import os
files_to_check = [
    'backend/app/services/llm_client.py',
    'backend/app/db/setup_db.py',
    '.env'
]

for file_path in files_to_check:
    if os.path.exists(file_path):
        print(f"✓ {file_path}: Exists")
    else:
        print(f"⚠ {file_path}: Missing")

print("\n" + "=" * 30)
print("Ready to run when dependencies are installed!")
print("\nTo install (if SSL works):")
print("pip install psycopg2-binary google-generativeai")