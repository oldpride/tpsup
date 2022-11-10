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

def exec_in_func(source:str):
    loc = locals()

    exec(source)
    print(f'in func: b={b}')
    a = loc['a']  # this makes a visible
    c = loc['c']  # this makes c visible
    print(f'in func: a={a} b={b} c={c}')

print(f'before: locals={locals()}{os.linesep}')

exec_in_func(source)

print(f'after: locals={locals()}{os.linesep}')


# a, c are not defined.
print(f'in main: a={a} b={b} c={c}')


