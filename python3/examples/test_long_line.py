#!/usr/bin/env python

line = "echo cmd"
for i in range(0, 30):
    line = f"{line} arg{i} "
print(line) # this long line is broken into multiple lines when copy-paste in gitbash and cygwin
# print(line, end='')  # this doesn't help
# print(line, width=10000)
