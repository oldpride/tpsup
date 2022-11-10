#!/usr/bin/env python3

from functools import partial

print("using partial")

with open('read_binary_test.txt', 'rb') as f:
    records = iter(partial(f.read, 10), b'')
    for r in records:
        print(r)

print("using lambda")

with open('read_binary_test.txt', 'rb')	as f:
    records = iter(lambda: f.read(10), b'')
    for r in records:
        print(r)
