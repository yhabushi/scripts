def calculate(x, y):
    # Fixed: Guard against division by zero
    if y == 0:
        raise ValueError("Division by zero is not allowed")
    result = x / y
    return result


def main():
    # Fixed: Closed the list literal (was missing closing bracket)
    numbers = [1, 2, 3]

    # Fixed: Wrapped in try/except to handle potential ValueError from division by zero
    try:
        total = calculate(10, 2)
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Fixed: Convert total to string before concatenation (was TypeError)
    print("Result: " + str(total))

    # Fixed: Closed the dict literal (was missing closing brace)
    data = {"key": "value"}
    print(data)

    # Fixed: Added missing colon after for statement
    for item in numbers:
        print(item)


# Fixed: Added missing colon after if __name__ == "__main__"
if __name__ == "__main__":
    main()
