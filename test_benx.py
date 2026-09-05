#!/usr/bin/env python3
"""
Quick test script for BenX AI
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from jarvis_ai.ai_engine import AIEngine
from jarvis_ai.config import Config

print("=" * 60)
print("Testing BenX AI Engine")
print("=" * 60)

# Test 1: Check API keys
print(f"\n1. API Keys configured:")
print(f"   Groq Key:       {'Yes (' + Config.GROQ_KEY[:10] + '...)' if Config.GROQ_KEY else 'No'}")
print(f"   OpenRouter Key: {'Yes (' + Config.OPENROUTER_KEY[:15] + '...)' if Config.OPENROUTER_KEY else 'No'}")

# Test 2: Check models
print(f"\n2. Available models: {len(Config.MODELS)}")
for i, model in enumerate(Config.MODELS[:6], 1):
    print(f"   {i}. {model}")

# Test 3: Simple query
print("\n3. Testing simple query...")
ai = AIEngine()
try:
    response = ai.chat("Say hello in one sentence")
    print(f"   Response: {response[:100]}...")
    print("   ✅ AI is working!")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 4: Command interpretation
print("\n4. Testing command interpretation...")
try:
    cmd = ai.interpret_command("open chrome")
    print(f"   Command: {cmd[:100]}...")
    print("   ✅ Command interpretation working!")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
