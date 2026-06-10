#!/bin/bash
set -euo pipefail

echo "Starting process..."

# 1. Fixed: Added quotes around variable to prevent unary operator error
#    Fixed: Use = instead of == for POSIX-compliant string comparison in [ ]
if [ "${UNDEFINED_VAR:-}" = "hello" ]; then
    echo "Found it"

    # 2. Fixed: Added 'done' to close the for loop
    for i in 1 2 3; do
        # Fixed: Quoted variable in echo
        echo "$i"
    done

# 3. Fixed: Added 'fi' to close the if block
fi

# 4. Fixed: Closed the double quote
echo "This line has a closed quote"

# 5. This line is now reachable
echo "Process complete"
