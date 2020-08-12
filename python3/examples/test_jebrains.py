import types

fv: types.FunctionType = None

def f():
    print("hello world")

fv = f

fv()