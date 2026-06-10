#!/bin/bash

echo "Starting process..."

# 1. Fixed: Quote the variable to avoid unary operator error when undefined
if [ "${UNDEFINED_VAR}" == "hello" ]; then
    echo "Found it"

    # 2. Fixed: Added missing 'done' to close the for loop
    for i in 1 2 3; do
        echo "$i"
    done

fi
# 3. Fixed: Restored the missing 'fi' to close the if block

# 4. Fixed: Closed the double quote
echo "This line has a closed quote"

# 5. Now reachable: process completes normally
echo "Process complete"
