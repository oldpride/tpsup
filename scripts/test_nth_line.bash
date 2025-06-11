#!/bin/bash

# https://stackoverflow.com/questions/6022384/bash-tool-to-get-nth-line-from-a-file
echo "1
2
3
4
5
6
7
" | sed "5q;d" # we see the 5th line, which is 5.

# NUMq will quit immediately when the line number is NUM.

# d will delete the line instead of printing it; this is inhibited 
# on the last line because the q causes the rest of the script to 
# be skipped when quitting.

echo "------------------------------"
echo "1
2
3
" | sed "5q;d"

echo "------------------------------"
echo "1
2
3
4
5
6
7
" | sed "5q;"

echo "------------------------------"
echo "1
2
3
4
5
6
7
" | sed "5d"
