#!/usr/bin/env python
import os
from tpsup.exectools import exec_into_globals
from pprint import pformat

source = '''
a=1

def f(n:int):
    return n+1

a=f(a)
b=f(b)
c=a+1
print(f'in exec: a={a} b={b} c={c}')
'''

b = 101

exec_into_globals(source, globals(), locals())

print(f'in main: a={a} b={b} c={c}')


def f2():
    print(f'in f2 before: a={a} b={b} c={c}')
    exec_into_globals(source, globals(), locals())
    print(f'in f2 after: a={a} b={b} c={c}')


f2()

print(f'in main: a={a} b={b} c={c}')
