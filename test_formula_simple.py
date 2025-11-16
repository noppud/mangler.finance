#!/usr/bin/env python3
"""
Simple test for formula update logic without imports.
"""

import re


def letter_to_column(letter: str) -> int:
    """Convert column letter to column number (A=1, B=2, ..., Z=26, AA=27, etc.)"""
    result = 0
    for char in letter:
        result = result * 26 + (ord(char) - ord("A") + 1)
    return result


def column_to_letter(column: int) -> str:
    letter = ""
    while column > 0:
        remainder = (column - 1) % 26
        letter = chr(65 + remainder) + letter
        column = (column - 1) // 26
    return letter


def adapt_formula_for_column(
    formula_pattern: str, target_col_letter: str, target_row: int, reference_row: int
) -> str:
    """
    Adapt a formula pattern for a specific column.

    For example, if pattern is "=B2/52" and target_col is "C",
    returns "=C2/52"
    """

    # Replace column references in the formula
    # Pattern: =B2/52 -> =C2/52 for column C

    # Find all cell references like B2, C5, etc.
    def replace_column(match):
        col = match.group(1)
        row = match.group(2)

        # If this references the reference row, update the column
        if int(row) == reference_row:
            return f"{target_col_letter}{row}"
        return match.group(0)

    # Match cell references (one or more letters followed by digits)
    adapted = re.sub(r"([A-Z]+)(\d+)", replace_column, formula_pattern)

    return adapted


# Test
print("=" * 80)
print("Testing Column Conversions")
print("=" * 80)

test_letters = ["A", "B", "Z", "AA", "AB", "AZ", "BA", "ZZ"]
expected_nums = [1, 2, 26, 27, 28, 52, 53, 702]

print("\nLetter to Number:")
for letter, expected in zip(test_letters, expected_nums):
    result = letter_to_column(letter)
    status = "✓" if result == expected else "✗"
    print(f"  {status} {letter:3s} -> {result:4d} (expected {expected:4d})")

print("\nNumber to Letter:")
for number, expected in zip(expected_nums, test_letters):
    result = column_to_letter(number)
    status = "✓" if result == expected else "✗"
    print(f"  {status} {number:4d} -> {result:3s} (expected {expected:3s})")

print("\n" + "=" * 80)
print("Testing Formula Adaptation")
print("=" * 80)

# Test generating formulas for B3:E3 with pattern =B2/52
print("\nGenerating formulas for B3:E3 with pattern '=B2/52':")
for col_num in range(2, 6):  # B(2) to E(5)
    col_letter = column_to_letter(col_num)
    formula = adapt_formula_for_column("=B2/52", col_letter, 3, 2)
    print(f"  Column {col_letter}: {formula}")

# Expected output:
# B: =B2/52
# C: =C2/52
# D: =D2/52
# E: =E2/52

print("\n" + "=" * 80)
print("Simulating the weekly income row update")
print("=" * 80)

# Simulate what the function will do for rangeStart=B3, rangeEnd=Z3
range_start = "B3"
range_end = "Z3"
formula_pattern = "=B2/52"
reference_row = 2

start_match = re.match(r"([A-Z]+)(\d+)", range_start)
end_match = re.match(r"([A-Z]+)(\d+)", range_end)

start_col_letter = start_match.group(1)
start_row = int(start_match.group(2))
end_col_letter = end_match.group(1)
end_row = int(end_match.group(2))

print(f"Range: {range_start}:{range_end}")
print(f"Start column: {start_col_letter} (number: {letter_to_column(start_col_letter)})")
print(f"End column: {end_col_letter} (number: {letter_to_column(end_col_letter)})")
print(f"Row: {start_row}")

start_col_num = letter_to_column(start_col_letter)
end_col_num = letter_to_column(end_col_letter)

formulas = []
for col_num in range(start_col_num, end_col_num + 1):
    col_letter = column_to_letter(col_num)
    formula = adapt_formula_for_column(formula_pattern, col_letter, start_row, reference_row)
    formulas.append(formula)

print(f"\nGenerated {len(formulas)} formulas:")
print(f"  First 5: {formulas[:5]}")
print(f"  Last 5: {formulas[-5:]}")

print("\n" + "=" * 80)
print("✓ ALL TESTS COMPLETED")
print("=" * 80)
