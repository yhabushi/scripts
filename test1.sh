#!/bin/bash
echo "Starting process..."
if [ $UNDEFINED_VAR == "hello" ]
then
    echo "Found it"
    for i in 1 2 3
    do
        echo $i
    # missing 'done'
fi
echo "This line has an unclosed quote
