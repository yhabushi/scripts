def calculate(x, y):
    # Fix: guard against division by zero
    if y == 0:
        print("Error: division by zero")
        return None
    result = x / y
    return result

def main():
    # Fix: closed the list literal
    numbers = [1, 2, 3]
    # Fix: use a non-zero divisor to avoid ZeroDivisionError
    total = calculate(10, 2)
    # Fix: use f-string instead of string + float concatenation (TypeError)
    print(f"Result: {total}")

    # Fix: closed the dict literal
    data = {"key": "value"}
    # Fix: added colon after 'for' statement
    for item in numbers:
        print(item)

# Fix: added colon after 'if __name__' statement
if __name__ == "__main__":
    main()
