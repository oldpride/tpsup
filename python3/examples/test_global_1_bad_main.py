#!/usr/bin/env python

# import from current folder
import os
import sys

sys.path.append(os.getcwd())
import test_global_1_bad_mod

test_global_1_bad_mod.mod_func(1)
print(globals()["from_mod_func"])
# this will error:
# KeyError: 'from_mod_func'
