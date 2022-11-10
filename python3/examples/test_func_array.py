#!/usr/bin/env python3

func_array = [
    lambda r:
        r['number'] + 1
    ,
    lambda r:
        r['number'] + 2
]

r = {'number': 100, 'string': 'hello'}

print(func_array[0](r))
print(func_array[1](r))
