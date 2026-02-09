#!/usr/bin/env python3
"""
Test script to verify Copilot Bridge connection and functionality.

Run this first to ensure Copilot Bridge is working correctly before running
the full grading tests.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.copilot_bridge_client import CopilotBridgeClient
from app.core.logging import get_logger

logger = get_logger()


def test_health_check():
    """Test if Copilot Bridge server is running."""
    print("\n" + "=" * 70)
    print("STEP 1: HEALTH CHECK")
    print("=" * 70)

    client = CopilotBridgeClient()
    is_healthy = client.health_check()

    if is_healthy:
        print("✓ Copilot Bridge server is running at http://localhost:1287")
        return True
    else:
        print("✗ Cannot connect to Copilot Bridge at http://localhost:1287")
        print("  Make sure VS Code with CopilotBridge extension is running")
        return False


def test_session_creation():
    """Test creating a new session."""
    print("\n" + "=" * 70)
    print("STEP 2: SESSION CREATION")
    print("=" * 70)

    client = CopilotBridgeClient()
    session_id = client.create_session()

    if session_id:
        print(f"✓ Created session: {session_id}")
        return client
    else:
        print("✗ Failed to create session")
        return None


def test_simple_query(client: CopilotBridgeClient):
    """Test a simple query to Copilot."""
    print("\n" + "=" * 70)
    print("STEP 3: SIMPLE QUERY TEST")
    print("=" * 70)

    prompt = "What is 2+2? Answer with just the number."
    print(f"Prompt: {prompt}")
    print("\nWaiting for response...")

    response = client.query(prompt, timeout=30)

    if response:
        print(f"\n✓ Got response from Copilot:")
        print(f"  {response}")
        return True
    else:
        print("✗ No response from Copilot")
        return False


def test_grading_query(client: CopilotBridgeClient):
    """Test a grading prompt similar to what the system will use."""
    print("\n" + "=" * 70)
    print("STEP 4: VOCABULARY GRADING PROMPT TEST")
    print("=" * 70)

    context = """
Student's homework extraction:
- Question 1: Student answered "weird" for "which word doesn't mean 'open'"
- Question 2: Student answered "strange" for "which word doesn't mean 'annoy'"  
- Question 3: Student answered "unfurl" for fill-in-the-blank about flags

Expected answers:
- Q1: "weird" is CORRECT (doesn't mean open)
- Q2: "strange" is WRONG (should be "lie")
- Q3: "unfurl" is CORRECT (flags unfurl in breeze)
"""

    prompt = """Please grade these vocabulary homework answers:
1. Mark each answer as correct (✓) or incorrect (✗)
2. For incorrect answers, provide a brief 1-sentence correction
3. Provide encouraging feedback overall

Format response as:
Q1: ✓/✗ - [comment if wrong]
Q2: ✓/✗ - [comment if wrong]  
Q3: ✓/✗ - [comment if wrong]
"""

    print(f"Grading prompt: {prompt[:100]}...")
    print("\nWaiting for grading response...")

    response = client.query(prompt, context=context, timeout=30)

    if response:
        print(f"\n✓ Got grading response:")
        print(f"  {response}")
        return True
    else:
        print("✗ No grading response from Copilot")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("COPILOT BRIDGE INTEGRATION TEST")
    print("=" * 70)
    print("Testing connection to VS Code Copilot Bridge")
    print("Expected: VS Code with CopilotBridge extension running")

    # Test 1: Health check
    if not test_health_check():
        print("\n❌ Cannot connect to Copilot Bridge")
        print("\nFix: Make sure VS Code with CopilotBridge extension is running:")
        print("  1. Open VS Code")
        print("  2. Install CopilotBridge extension")
        print("  3. Keep VS Code open in background")
        return False

    # Test 2: Session creation
    client = test_session_creation()
    if not client:
        return False

    # Test 3: Simple query
    if not test_simple_query(client):
        print("\n⚠️  Simple query failed. Check if Copilot is properly configured.")
        return False

    # Test 4: Grading query
    if not test_grading_query(client):
        print("\n⚠️  Grading query failed.")
        return False

    # Cleanup
    client.close_session()

    print("\n" + "=" * 70)
    print("✓ ALL TESTS PASSED")
    print("=" * 70)
    print("\nCopilot Bridge is ready for use!")
    print("You can now run the vocabulary grading test with real AI.")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
