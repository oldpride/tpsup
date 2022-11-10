#!/usr/bin/env python3

# https://stackoverflow.com/questions/15086040/behavior-of-exec-function-in-python-2-and-python-3
# https://docs.python.org/3/library/functions.html#exec


# def execute(st):
#     b = 42
#     #d = locals()
#     d = {}
#     exec("b = {}\nprint('b:', b)".format(st), globals(), d)
#     print(b)  # This prints 42
#     print(d['b'])  # This prints 1000000.0
#     print(id(d) == id(locals()))  # This prints True
#
#     func = """
# def temp(a):
#     return a+3
# """
#     # exec in the namespace
#     exec(f'{func}', globals(), d)
#     exec(f'print(temp(b))', globals(), d)
#
#
# a = 1
# execute("1.E6*a")

def execute(statement, namespace):
    exec(statement, globals(), namespace)

exp_namespace = {}

print(f'1 =  {exp_namespace}')

func = """
def temp(a):
    return a+3
"""
execute(func, exp_namespace)

print(f'2 =  {exp_namespace}')

print('3 = from exec, b=')
exec(f'b=temp(1);print(b)', globals(), exp_namespace)

print(f'4 =  {exp_namespace}')


# def u():
#     l = locals()
#     print(l)
#     a = 1
#     print(l)
#     print(locals())
#     print(l)
#
# u()
