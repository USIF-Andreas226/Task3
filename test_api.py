#!/usr/bin/env python3
"""
Test script to verify OpenRouter API key is working.
Run: python3 test_api.py
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load from .env in current directory
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.environ.get("OPENROUTER_API_KEY", "NOT_SET")
mongo_uri = os.environ.get("MONGO_URI", "NOT_SET")
username = os.environ.get("LOGIN_USERNAME", "NOT_SET")

print("=" * 60)
print("CONFIGURATION CHECK")
print("=" * 60)

print("\n📋 Current .env Settings:")
print(f"  LOGIN_USERNAME: {username}")
print(f"  MONGO_URI: {mongo_uri[:50]}..." if len(mongo_uri) > 50 else f"  MONGO_URI: {mongo_uri}")

if api_key == "NOT_SET":
    print(f"  OPENROUTER_API_KEY: ❌ NOT SET")
elif api_key.startswith("sk-or-v1-local") or "replace" in api_key.lower() or "<" in api_key:
    print(f"  OPENROUTER_API_KEY: ❌ PLACEHOLDER (needs real key)")
    print(f"    Current value: {api_key}")
else:
    print(f"  OPENROUTER_API_KEY: {api_key[:30]}...")

print("\n" + "=" * 60)
print("TESTING API CONNECTION")
print("=" * 60)

if api_key == "NOT_SET":
    print("\n❌ ERROR: OPENROUTER_API_KEY is not set")
    print("\nFix:")
    print("  1. Get a real API key from: https://openrouter.ai")
    print("  2. Update .env: OPENROUTER_API_KEY=sk-or-v1-your-real-key")
    print("  3. Run this script again")
    exit(1)

if api_key.startswith("sk-or-v1-local") or "replace" in api_key.lower() or "<" in api_key:
    print("\n❌ ERROR: API key is still a placeholder!")
    print(f"   Current value: {api_key}")
    print("\nFix:")
    print("  1. Go to: https://openrouter.ai")
    print("  2. Sign in → Profile → API Keys")
    print("  3. Copy your real API key (starts with sk-or-v1-)")
    print("  4. Update .env file:")
    print("     OPENROUTER_API_KEY=sk-or-v1-your-real-key-here")
    print("  5. Run this script again")
    exit(1)

# Try to use the API
print("\n🔌 Testing OpenRouter API connection...")

try:
    from openai import OpenAI
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://kayfa.com",
            "X-Title": "Kayfa AI Sales Agent",
        },
    )
    
    print("   Sending test request to OpenRouter...")
    
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b:free",
        messages=[
            {"role": "user", "content": "Say 'OpenRouter API is working!' in English only."}
        ],
        max_tokens=50,
    )
    
    result = response.choices[0].message.content.strip()
    print(f"\n✅ SUCCESS! API is working!")
    print(f"   Response: {result}")
    print("\n   Your app will now generate AI-powered responses instead of fallback messages!")
    
except Exception as e:
    print(f"\n❌ API Error: {type(e).__name__}: {str(e)}")
    print("\nPossible causes:")
    print("  1. API key is invalid or expired")
    print("  2. Free tier quota exceeded (limited requests/month)")
    print("  3. OpenRouter account is not active")
    print("  4. Network/firewall issue")
    print("\nFix:")
    print("  • Verify API key at: https://openrouter.ai/settings/keys")
    print("  • Check account quota at: https://openrouter.ai/account/usage")
    print("  • Try regenerating the API key")
    exit(1)
