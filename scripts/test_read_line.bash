#!/usr/bin/bash

lines="
this is line 1
this is line 2
"

echo "$lines" | while read line;
do
echo "read line: $line"
done

echo "$lines" |tac | while read line;
do
echo "read reverse line: $line"
done
