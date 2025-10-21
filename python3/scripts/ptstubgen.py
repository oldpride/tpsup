#! /usr/bin/env python

# https://stackoverflow.com/questions/49409249/python-generate-function-stubs-from-c-module

import argparse
import importlib
import os
import sys
import textwrap
from pprint import pformat
import traceback
import inspect

prog = os.path.basename(sys.argv[0])
script_dir = os.path.dirname(sys.argv[0])
# get absolute path of script_dir
script_dir = os.path.abspath(script_dir)


usage = textwrap.dedent(f"""
    Enhanced 'stubgen'
                        
    {prog} module_name

    """)

examples = textwrap.dedent(f""" 
    $ freecadenv set         # set up freecad env first
    $ which python           # this python should be under freecad installation.
    $ cdwhich freecadcmd     # go to freecadcmd location
    $ sudo python -d . "{script_dir}/{prog}" FreeCAD  # need sudo to write to freecad site-packages.
    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    epilog=examples,
    description=usage,
    # formatter_class=argparse.RawTextHelpFormatter, # this honors \n but messed up indents
    formatter_class=argparse.RawDescriptionHelpFormatter
)

parser.add_argument(
    '-v', '--verbose', default=0, action="count",
    help='verbose level: -v, -vv, -vvv')

parser.add_argument(
    '-d', '--outdir', default='.',
    help='output directory for the generated stub files')

parser.add_argument(
    # args=argparse.REMAINDER indicates optional remaining args and stored in a List
    'remainingArgs', nargs=argparse.REMAINDER,
    help='remaining args: module_name')

args = vars(parser.parse_args())
# default to parse command line args. we can also parse any list: args = vars(parser.parse_args(['hello', 'world'))

remaining_args: list[str] = args['remainingArgs']  # python casting, type hint, typing hint
if len(remaining_args) != 1:
    print(f"{prog}: error: wrong number of arguments\n")
    parser.print_help()
    sys.exit(1)
module_name: str = remaining_args[0]  # python casting, type hint, typing hint

verbose = args['verbose']

if verbose:
    sys.stderr.write("args =\n")
    sys.stderr.write(pformat(args) + "\n")

try:
    imported = importlib.import_module(module_name)
    print(f"module {module_name} imported successfully")
    # try to get module version
except Exception as e:
    print(f"module {module_name} import failed: {e}")
    traceback.print_exc()
with open(f"{args['outdir']}/{module_name}.pyi", 'w') as f:
    for name, obj in inspect.getmembers(imported):
        if inspect.isclass(obj):
            f.write('\n')
            f.write(f'class {name}:\n')

            for func_name, func in inspect.getmembers(obj):
                if not func_name.startswith('__'):
                    try:
                        f.write(f'    def {func_name} {inspect.signature(func)}:\n')
                    except Exception as e:
                        if verbose:
                            print(f"failed to get signature for {func_name}: {e}")
                        f.write(f'    def {func_name} (self, *args, **kwargs):\n')
                    f.write(f"      '''{func.__doc__}'''")
                    f.write('\n    ...\n')
