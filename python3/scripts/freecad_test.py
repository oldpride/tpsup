#! /usr/bin/env python

import sys
import importlib
import os
import traceback
from pprint import pformat
prog = os.path.basename(sys.argv[0])

usage = f""" 
Check freecad python

usage:
    set up env
        freecadenv set
        which freecadcmd
        which python # this python should be under freecad installation.

    freecadcmd is a python-like command, you can run
        freecadcmd test.py

    so we can run it with chkpython.py
        freecadcmd {prog}

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
print("python search path, sys.path:")
for p in sys.path:
    print(f"    {p}")
print()

# print PYTHONPATH env variable. this is different from sys.path
pythonpath = os.environ.get('PYTHONPATH', '')
print(f"PYTHONPATH={pythonpath}")
print()

# try to import the module
module_names = [
    
    # the following files are .pyd files. 'pyd' files are like .dll files.
    # therefore vscode can import them but pylance cannot find their source code.
    # so pylance will report "import could not be resolved" error.
    # a workaround is to create a stub file (.pyi) for each module using
    # mypy's stubgen tool or our enhanced ptstubgen.py script.    
    'FreeCAD',  # I made a stub file FreeCAD.pyi for it using ptstubgen.py.
    'Part',
    'Sketcher',
    'FreeCADGui',

    # FreeCAD GUI is built on top of PySide2.
    'PySide2',

    # test PyQt
    'PyQt',
    'PyQt2',

    'pip',   # pip command does not exist under freecad, but pip module should exist
    'mypy',  # this has stubgen


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
        continue

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

    
