#!/usr/bin/env python

line = "echo cmd"
for i in range(0, 20):
    line = f"{line} arg{i} "
print(line)
