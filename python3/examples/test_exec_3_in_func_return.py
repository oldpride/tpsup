#!/use/bin/env python
import os

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

global_locals = {}

def exec_in_func(source:str):
    global global_locals
    loc = locals() # this makes b visible. likely without this, other vars are optimized to invisible
    exec(source)
    global_locals = loc

print(f'before: global_locals={global_locals}{os.linesep}')

exec_in_func(source)

print(f'after: global_locals={global_locals}{os.linesep}')

locals().update(global_locals)
# a, c are not defined.
print(f'in main: a={a} b={b} c={c}')


