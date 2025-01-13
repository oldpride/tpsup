#!/usr/bin/env python

from pprint import pformat
x = { 'a': 1, 'b': 2}
y = { 'a': 2, 'c': 3}

m1 = {**x, **y}
m2 = x|y  # python 3.9+

print(f"m1 = {pformat(m1)}")
print(f"m2 = {pformat(m2)}")