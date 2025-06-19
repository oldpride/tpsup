#!/bin/bash

lines="
1
2
3
"

# problem: the variable 'count' is not preserved across the subshells created by the pipe.
count=0
echo "$lines" | while read line;
do
    count=$((count + 1))
done
echo "count #1: $count" # should be 0, undesirable behavior.

# solution1: use here-string syntax to avoid subshells.
count=0
while read line;
do
    count=$((count + 1))
done <<< "$lines" # here-string syntax
echo "count #2: $count" # should be > 0, desirable behavior.

# solution2: pick the value from subshell.
count=0
count=$(
   echo "$lines" | (while read line;
   do
       count=$((count + 1))
   done; echo "$count")
)
echo "count #3: $count" # should be > 0, desirable behavior.
