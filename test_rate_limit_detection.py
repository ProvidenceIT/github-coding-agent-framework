#!/usr/bin/env python3
"""
Test script to verify rate limit detection works correctly.
"""
import sys
import logging
from pathlib import Path

# Add parent directory to path to import autonomous_agent modules
sys.path.insert(0, str(Path(__file__).parent))

from token_rotator import TokenRotator, get_rotator, set_rotator

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import after setting up path
from autonomous_agent_fixed import analyze_session_health

def test_rate_limit_detection():
    """Test that rate limit patterns are detected in responses."""

    print("="*60)
    print("Testing Rate Limit Detection")
    print("="*60)

    # Initialize token rotator
    rotator = TokenRotator.from_env()
    set_rotator(rotator)

    print(f"\nInitial token: {rotator.current_name}")
    print(f"Available tokens: {rotator.available_count}/{len(rotator.tokens)}\n")

    # Test cases with rate limit messages
    test_cases = [
        {
            'name': 'Rate limit message',
            'response': 'I encountered a rate limit error while processing your request.',
            'should_detect': True
        },
        {
            'name': 'HTTP 429',
            'response': 'Error: HTTP 429 - Too many requests',
            'should_detect': True
        },
        {
            'name': 'Quota exceeded',
            'response': 'Sorry, your quota has been exceeded. Please try again later.',
            'should_detect': True
        },
        {
            'name': 'Capacity message',
            'response': 'The system is currently at capacity. Please retry.',
            'should_detect': True
        },
        {
            'name': 'Normal response',
            'response': 'Here is the file content you requested. The code looks good.',
            'should_detect': False
        },
    ]

    results = []
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['name']}")
        print(f"Response: {test['response'][:60]}...")

        # Reset rotator state before each test
        initial_token = rotator.current_name

        # Run health check
        health = analyze_session_health(
            response=test['response'],
            session_id=f"test_{i}",
            logger=logger,
            tool_count=5  # Fake tool count to keep health check happy
        )

        detected = health.get('rate_limit_detected', False)
        current_token = rotator.current_name
        rotated = (current_token != initial_token)

        print(f"  Rate limit detected: {detected}")
        print(f"  Token rotated: {rotated} (from {initial_token} to {current_token})")

        # Check if detection matches expectation
        if detected == test['should_detect']:
            print(f"  ✅ PASS")
            results.append(True)
        else:
            print(f"  ❌ FAIL - Expected detection: {test['should_detect']}, Got: {detected}")
            results.append(False)

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Final token: {rotator.current_name}")

    rotator.print_status()

    if passed == total:
        print("\n✅ All tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed!")
        return 1

if __name__ == "__main__":
    exit(test_rate_limit_detection())
