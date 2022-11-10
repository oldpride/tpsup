#!/usr/bin/env python
import re
import types
import copy
from typing import Callable
from pprint import pformat
import tpsup.modtools

def copy_func(f: Callable, name=None):
    """
    return a function with same code, globals, defaults, closure, and
    name (or provide a new name)

    https://stackoverflow.com/questions/6527633/how-can-i-make-a-deepcopy-of-a-function-in-python/30714299#30714299
    """
    new_globals: dict = f.__globals__.copy()
    keys = list(new_globals.keys())
    for key in keys:
        if not re.match("__", key):  # re.match() starts from beginning
            new_globals.pop(key)  # delete a dictionary key
    new_code = copy.deepcopy(f.__code__)
    print(f"code type={type(f.__code__)}")
    #fn = types.FunctionType(f.__code__, new_globals, name or f.__name__,f.__defaults__, f.__closure__)
    fn = types.FunctionType(new_code, new_globals, name or f.__name__, f.__defaults__, f.__closure__)

    # https://stackoverflow.com/a/56901529/5128398
    fn.__qualname__ = "f2"

    fn.__dict__.update(f.__dict__)
    print(f"__code__={pformat(fn.__code__)}")
    print(f"__globals__={pformat(fn.__globals__)}")
    print(f"__name__={pformat(fn.__name__)}")
    print(f"__defaultgs__={pformat(fn.__defaults__)}")
    print(f"__closure__={pformat(fn.__closure__)}")
    if name:
        fn.__name__ = name
    # in case f was given attrs (note this dict is a shallow copy):
    return fn

def f1():
    print("in f1")
    pass

f2 = copy_func(f1, name="f2")
print(f"f1={f1}")
print(f"f2={f2}")

#mod = tpsup.modtools.load_module(f1.__code__, function_name='f1_in_mod')
mod = tpsup.modtools.load_module(f1, function_name='f1_in_mod')
mod.f1_in_mod()
f2()
