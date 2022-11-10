#!/use/bin/env python



source = '''
a=1

def f(n:int):
    return n+1

a=f(a)
b=f(b)
print(f'in exec: a={a} b={b}')
'''

b=101

exec(source)

print(f'in main: a={a} b={b}')

c=f(b)
print(f'c={c}')

print('if exec is not called inside a function, very easy to work with, very intuitive')