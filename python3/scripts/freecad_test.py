#! /usr/bin/env python

import sys
import importlib
import os
import traceback
import argparse
import textwrap
from pprint import pformat
prog = os.path.basename(sys.argv[0])

usage = """ 
Check freecad python

usage:
    freecadcmd is a python-like command, you can run
        freecadenv set
        freecadcmd test.py

    so we can run it with chkpython.py
        freecadcmd chkpython.py

    it will print out
        - python search path
        - python version
        - if module_name can be imported
        - module version if possible
        - module file location if possible

"""

# print python version
python_version = sys.version.replace('\n', ' ')
print(f"python version={python_version}")

# print python search path
print("python search path:")
for p in sys.path:
    print(f"    {p}")
# try to import the module
module_names = [
    'FreeCAD',
    # 'FreeCAD' is the main module, but it is not a file.
    # we cannot get its file location.
]

for module_name in module_names:
    print("\n----------------------------------------")
    imported = None
    try:
        imported = importlib.import_module(module_name)
        print(f"module {module_name} imported successfully")
        # try to get module version
    except Exception as e:
        print(f"module {module_name} import failed: {e}")
        traceback.print_exc()
        sys.exit(1)

    try:
        module_version = imported.__version__
        print(f"module {module_name} version={module_version}")
    except Exception as e:
        print(f"module {module_name} version not found: {e}")

    module_file = getattr(imported, '__file__', None)
    if module_file:
        print(f"module {module_name} file location: {module_file}")
    else:
        print(f"module {module_name} file location not found")

    
