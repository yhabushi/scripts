#!/bin/bash
set -euo pipefail

echo "Starting process..."

# 1. Fixed: Quote the variable to prevent unary operator error when unset/empty
#    Also use = instead of == for POSIX compatibility in [ ]
if [ "${UNDEFINED_VAR:-}" = "hello" ]; then
    echo "Found it"

    # 2. Fixed: Added closing 'done' for the for loop
    for i in 1 2 3; do
        echo "$i"
    done

fi
# 3. Fixed: Restored 'fi' to close the if block

# 4. Fixed: Closed the double quote
echo "This line has a properly closed quote"

# 5. This code is now reachable
echo "Process complete"
