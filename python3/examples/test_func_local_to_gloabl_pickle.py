#!/usr/bin/env python
import types
import pickle

gf = None

def f ():
    def lf (n):
        print(n)

    global gf
    # gf = lf
    gf = types.FunctionType(lf.__code__, lf.__globals__, "gf", None, None)
    gf.__qualname__ = "gf"

    gf(1)

f()
gf(2)

def f2():
    def lf2 (n):
        print(2, n)

    global gf
    gf = types.FunctionType(lf2.__code__, lf2.__globals__, "gf", None, None)
    gf.__qualname__ = "gf"
    pickled_gf2 = pickle.dumps(gf, protocol=4)
    unpickled_gf2 = pickle.loads(pickled_gf)

    unpickled_gf2(4)


pickled_gf = pickle.dumps(gf, protocol=4)
unpickled_gf = pickle.loads(pickled_gf)

unpickled_gf(3)
f2()
gf(5)

