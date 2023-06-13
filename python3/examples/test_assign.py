#!/usr/bin/env python

for row in [
    [1],
    [1, 2],
    [1, 2, 3],
    [1, 2, 3, 4],
    [1, 2, 3, 4, 5],
]:
    # note,
    # 1. use '+' to concatenate two lists
    # 2. use '*' to repeat a list
    # 3. use 'None' to fill up the list
    # 4. repeat 'None' twice to fill up the list
    arg1, arg2, *rest = row + [None]*2
    print(f"row={row}, arg1={arg1}, arg2={arg2}, rest={rest}")
    print("")

# result:
# row=[1], arg1=1, arg2=None, rest=[None]
# row=[1, 2], arg1=1, arg2=2, rest=[None, None]
# row=[1, 2, 3], arg1=1, arg2=2, rest=[3, None, None]
# row=[1, 2, 3, 4], arg1=1, arg2=2, rest=[3, 4, None, None]
# row=[1, 2, 3, 4, 5], arg1=1, arg2=2, rest=[3, 4, 5, None, None]
