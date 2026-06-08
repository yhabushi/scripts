#!/bin/bash

echo "Starting process..."

# 1. Fix: Quoted variable + POSIX-compatible = operator
if [ "$UNDEFINED_VAR" = "hello" ]
then
    echo "Found it"

    # 2. Fix: Added 'done' to close the for loop
    for i in 1 2 3
    do
        echo $i
    done

# 3. Fix: Uncommented 'fi' so the if block is properly closed
fi

# 4. Fix: Closed the double quote
echo "This line has an unclosed quote"

# 5. This line is now reachable
echo "Process complete"
