#!/usr/bin/env python3
"""
Test script to verify the URL parsing fix works correctly.
"""

import sys
from pathlib import Path

# Add python_backend to path
sys.path.insert(0, str(Path(__file__).parent / "python_backend"))

from python_backend.utils import parse_spreadsheet_url, normalize_spreadsheet_id


def test_url_parsing():
    """Test various URL formats."""

    test_cases = [
        {
            "input": "https://docs.google.com/spreadsheets/d/1cRJNLsoww3OVcZ-PXI6QJac58E167R8OEii0WCcXvM4/edit?gid=0",
            "expected_id": "1cRJNLsoww3OVcZ-PXI6QJac58E167R8OEii0WCcXvM4",
            "expected_gid": "0",
            "description": "Full URL with gid"
        },
        {
            "input": "https://docs.google.com/spreadsheets/d/abc123xyz/edit",
            "expected_id": "abc123xyz",
            "expected_gid": None,
            "description": "URL without gid"
        },
        {
            "input": "abc123xyz",
            "expected_id": "abc123xyz",
            "expected_gid": None,
            "description": "Bare ID"
        },
        {
            "input": "https://docs.google.com/spreadsheets/d/test-id-123/edit?gid=456",
            "expected_id": "test-id-123",
            "expected_gid": "456",
            "description": "URL with gid=456"
        },
    ]

    print("=" * 80)
    print("Testing parse_spreadsheet_url()")
    print("=" * 80)

    all_passed = True

    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['description']}")
        print(f"  Input: {test['input']}")

        result = parse_spreadsheet_url(test['input'])

        print(f"  Result: {result}")
        print(f"  Expected ID: {test['expected_id']}")
        print(f"  Expected gid: {test['expected_gid']}")

        id_match = result["spreadsheet_id"] == test['expected_id']
        gid_match = result["gid"] == test['expected_gid']

        if id_match and gid_match:
            print("  ✓ PASS")
        else:
            print("  ✗ FAIL")
            if not id_match:
                print(f"    ID mismatch: got '{result['spreadsheet_id']}', expected '{test['expected_id']}'")
            if not gid_match:
                print(f"    gid mismatch: got '{result['gid']}', expected '{test['expected_gid']}'")
            all_passed = False

    print("\n" + "=" * 80)
    print("Testing normalize_spreadsheet_id()")
    print("=" * 80)

    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['description']}")
        print(f"  Input: {test['input']}")

        result = normalize_spreadsheet_id(test['input'])

        print(f"  Result: {result}")
        print(f"  Expected: {test['expected_id']}")

        if result == test['expected_id']:
            print("  ✓ PASS")
        else:
            print("  ✗ FAIL")
            print(f"    Got '{result}', expected '{test['expected_id']}'")
            all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 80)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(test_url_parsing())
