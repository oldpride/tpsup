#!/usr/bin/env python
import types
from typing import Callable

def copy_func(f: Callable, name=None):

    fn = types.FunctionType(f.__code__, f.__globals__,
                            name or f.__name__,f.__defaults__, f.__closure__)
    fn.__dict__.update(f.__dict__)
    fn.__qualname__ = 'f2'
    return fn

def f1():
    pass

f2 = copy_func(f1, name="f2")
print(f"f1={f1}")
print(f"f2={f2}")

print(f"f2.__code__={f2.__code__}")