#!/usr/bin/env python3


def calculate(x, y):
    # Fixed: Guard against division by zero
    if y == 0:
        raise ValueError("Division by zero is not allowed")
    result = x / y
    return result


def main():
    # Fixed: Closed the list literal (was missing closing bracket)
    numbers = [1, 2, 3]

    # Fixed: Wrapped in try/except to handle ZeroDivisionError;
    # calculate(10, 0) would raise ValueError with the guard above
    try:
        total = calculate(10, 0)
    except ValueError as e:
        print(f"Error: {e}")
        total = 0

    # Fixed: Convert total to str before concatenation (was a type error)
    print("Result: " + str(total))

    # Fixed: Closed the dict literal (was missing closing brace)
    data = {"key": "value"}
    print(f"Data: {data}")

    # Fixed: Added colon after 'for' statement
    for item in numbers:
        print(item)


# Fixed: Added colon after '__main__' condition
if __name__ == "__main__":
    main()
