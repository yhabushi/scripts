#!/usr/bin/env python3
"""
test.py - fixed version.

Bugs fixed:
  - calculate(10, 0) caused ZeroDivisionError; guard added and call changed to (10, 2).
  - "Result: " + total raised TypeError (float + str); fixed with str(total).
  - numbers = [1, 2, 3 was missing closing ]; fixed.
  - data = {"key": "value" was missing closing } and was never used; removed (dead code).
  - for item in numbers was missing its colon; fixed.
  - if __name__ == "__main__" was missing its colon; fixed.
"""


def calculate(x: float, y: float) -> float:
    """Return x / y. Raises ValueError on division by zero."""
    if y == 0:
        raise ValueError("Division by zero is not allowed.")
    return x / y


def main() -> None:
    numbers = [1, 2, 3]                    # fixed: closed list literal

    try:
        total = calculate(10, 2)            # fixed: was calculate(10, 0) -> ZeroDivisionError
    except ValueError as exc:
        print(f"Error: {exc}")
        return

    print("Result: " + str(total))          # fixed: str() cast prevents TypeError

    for item in numbers:                    # fixed: added colon
        print(item)


if __name__ == "__main__":                  # fixed: added colon
    main()
