import types
from typing import Optional, Callable, Union

fv: Optional[types.FunctionType] = None

def f(f2: Optional[Callable] = None):
    print("hello world")

fv = f

fv()