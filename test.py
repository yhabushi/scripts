def calculate(x, y):
    if y == 0:
        raise ValueError("Division by zero is not allowed.")
    result = x / y
    return result


def main():
    numbers = [1, 2, 3]
    try:
        total = calculate(10, 0)
        print("Result: " + str(total))
    except ValueError as e:
        print(f"Error: {e}")

    data = {"key": "value"}
    for item in numbers:
        print(item)


if __name__ == "__main__":
    main()
