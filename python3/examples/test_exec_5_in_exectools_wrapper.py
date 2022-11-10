#!/use/bin/env python
import os
from tpsup.exectools import  exec_into_globals
from pprint import pformat

def exec_simple(source):
    return exec_into_globals(source, globals(), locals())


source = '''
a=1

def f(n:int):
    return n+1

a=f(a)
b=f(b)
c=a+1
print(f'in exec: a={a} b={b} c={c}')
'''

b=101

def f2():
    exec_simple(source)
    print(f'in f2: a={a} b={b} c={c}')

f2()

print(f'in main: a={a} b={b} c={c}')

print(f'f(1)={f(1)}')

