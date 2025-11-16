#!/usr/bin/env python3
"""
Test the formula update functionality.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "python_backend"))

from python_backend.modifier import SheetModifier


def test_letter_to_column():
    """Test column letter to number conversion."""
    test_cases = [
        ("A", 1),
        ("B", 2),
        ("Z", 26),
        ("AA", 27),
        ("AB", 28),
        ("AZ", 52),
        ("BA", 53),
        ("ZZ", 702),
    ]

    print("=" * 80)
    print("Testing _letter_to_column()")
    print("=" * 80)

    all_passed = True
    for letter, expected in test_cases:
        result = SheetModifier._letter_to_column(letter)
        status = "✓" if result == expected else "✗"
        print(f"{status} {letter:3s} -> {result:4d} (expected {expected:4d})")
        if result != expected:
            all_passed = False

    return all_passed


def test_column_to_letter():
    """Test column number to letter conversion."""
    from python_backend.utils import column_to_letter

    test_cases = [
        (1, "A"),
        (2, "B"),
        (26, "Z"),
        (27, "AA"),
        (28, "AB"),
        (52, "AZ"),
        (53, "BA"),
        (702, "ZZ"),
    ]

    print("\n" + "=" * 80)
    print("Testing column_to_letter()")
    print("=" * 80)

    all_passed = True
    for number, expected in test_cases:
        result = column_to_letter(number)
        status = "✓" if result == expected else "✗"
        print(f"{status} {number:4d} -> {result:3s} (expected {expected:3s})")
        if result != expected:
            all_passed = False

    return all_passed


def test_adapt_formula():
    """Test formula adaptation for columns."""
    test_cases = [
        {
            "pattern": "=B2/52",
            "target_col": "C",
            "reference_row": 2,
            "expected": "=C2/52",
        },
        {
            "pattern": "=B2/52",
            "target_col": "D",
            "reference_row": 2,
            "expected": "=D2/52",
        },
        {
            "pattern": "=B2/52",
            "target_col": "Z",
            "reference_row": 2,
            "expected": "=Z2/52",
        },
        {
            "pattern": "=B2*2",
            "target_col": "E",
            "reference_row": 2,
            "expected": "=E2*2",
        },
        {
            "pattern": "=SUM(B2:B10)",
            "target_col": "C",
            "reference_row": 2,
            "expected": "=SUM(C2:B10)",  # Only first B2 gets replaced
        },
    ]

    print("\n" + "=" * 80)
    print("Testing _adapt_formula_for_column()")
    print("=" * 80)

    all_passed = True
    for i, test in enumerate(test_cases, 1):
        result = SheetModifier._adapt_formula_for_column(
            test["pattern"],
            test["target_col"],
            3,  # target_row (not used in formula adaptation)
            {"referenceRow": test["reference_row"]},
        )
        status = "✓" if result == test["expected"] else "✗"
        print(
            f"{status} Test {i}: {test['pattern']:20s} + col {test['target_col']} -> {result:20s} (expected {test['expected']})"
        )
        if result != test["expected"]:
            all_passed = False

    return all_passed


if __name__ == "__main__":
    passed1 = test_letter_to_column()
    passed2 = test_column_to_letter()
    passed3 = test_adapt_formula()

    print("\n" + "=" * 80)
    if passed1 and passed2 and passed3:
        print("✓ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("✗ SOME TESTS FAILED")
        sys.exit(1)
