#!/usr/bin/env python

# import from current folder
import os
import sys
import pprint

sys.path.append(os.getcwd())
import test_global_2_ok_mod

test_global_2_ok_mod.mod_func(1, globals())
# pprint.pprint(globals())
print(globals()["from_mod_func"])

# this doesn't work
# print(globals().from_mod_func)
# AttributeError: 'dict' object has no attribute 'from_mod_func'
