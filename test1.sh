#!/bin/bash
# Demonstration script - fixed version
set -euo pipefail

echo "Starting process..."

# Fix 1: Quote the variable and provide a default to avoid
#         "unary operator expected" when UNDEFINED_VAR is empty or unset.
#         Also use POSIX-compatible single = instead of ==.
if [ "${UNDEFINED_VAR:-}" = "hello" ]; then
    echo "Found it"

    # Fix 2: Added missing 'done' to close the for loop.
    for i in 1 2 3; do
        echo "$i"    # Fix 3: Quoted $i to prevent word-splitting.
    done

fi  # Fix 4: Restored missing 'fi' to close the if block.

# Fix 5: Closed the unclosed double quote.
echo "This line has a properly closed quote"

# Fix 6: This line is now reachable (was dead code due to the errors above).
echo "Process complete"
