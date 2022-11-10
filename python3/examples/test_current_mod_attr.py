#!/usr/bin/env python

from pprint import pformat
import sys

mod = sys.modules[__name__]

a= 1
def f1(n):
    return n+1
a=f1(a)
print(f'a1={a}')

mod.__dict__['a'] = 3
print(f'a2={a}')

def f2(dict):
    dict.update({'a': 4})

f2(mod.__dict__)

print(f'a3={a}')

print(f'dir() = {dir(mod)}')
print(f'__dict__={pformat(mod.__dict__)}')