#!/bin/bash

echo "Starting process..."

# 1. Potential Unary Operator Error (Missing quotes around variable)
if [ $UNDEFINED_VAR == "hello" ]
then
    echo "Found it"
    
    # 2. Syntax Error: Missing 'done' to close the loop
    for i in 1 2 3
    do
        echo $i
    
# 3. Syntax Error: Missing 'fi' (The shell will think 'fi' below is part of the string)
# fi 

# 4. Critical Syntax Error: Unclosed double quote
echo "This line has an unclosed quote

# 5. Logic Error: This code is unreachable because of the errors above
echo "Process complete"
