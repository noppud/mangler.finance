#!/usr/bin/env python3
"""
Test the JSON truncation detection logic.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "python_backend"))

from python_backend.llm import LLMClient


def test_truncation_detection():
    """Test the _detect_json_truncation method."""

    # Create a dummy LLM client (we won't actually call the API)
    client = LLMClient(
        api_key="dummy",
        model="dummy",
        base_url="http://dummy",
        temperature=0.7,
        max_tokens=4000,
    )

    test_cases = [
        # Valid JSON - should NOT detect truncation
        ('{"intent": "test", "actions": []}', False, "Valid complete JSON"),
        ('{"key": "value"}', False, "Simple valid JSON"),
        ('[1, 2, 3]', False, "Valid JSON array"),

        # Truncated JSON - should detect truncation
        ('{"intent": "test", "actions": [{"type":', True, "Ends with colon"),
        ('{"intent": "test", "actions"', True, "Missing closing bracket"),
        ('{"intent": "test", "actions": [{"type": "batch_update"', True, "Unclosed object"),
        ('{"key": "value",', True, "Ends with comma"),
        ('{"key": "val', True, "Ends mid-value"),
        ('{"a": {"b": {"c": 1}', True, "Unclosed nested objects"),
    ]

    print("=" * 80)
    print("Testing JSON Truncation Detection")
    print("=" * 80)

    all_passed = True
    for json_str, expected, description in test_cases:
        result = client._detect_json_truncation(json_str)
        status = "✓" if result == expected else "✗"
        print(f"{status} {description:30s} | Expected: {str(expected):5s} | Got: {str(result):5s}")

        if result != expected:
            all_passed = False
            print(f"   JSON: {json_str[:50]}...")

    print("\n" + "=" * 80)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(test_truncation_detection())
