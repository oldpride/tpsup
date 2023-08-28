#!/usr/bin/env python

import argparse
import sys
import textwrap
from pprint import pformat
import os

prog = os.path.basename(sys.argv[0])

usage = textwrap.dedent(""""\
        test argparse nargs, mixing positional and optional arguments
        """)

examples = textwrap.dedent(f""" 
                            
    examples:
        
        {prog} -a 1 p1 -b b1
""")

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

parser.add_argument(
    'p', default=[],

    # positional arguments starts from the first one that is not optional
    # nargs=argparse.REMAINDER

    # mixed positional and optional arguments.
    # nargs="*", # 0 or more positional arguments.
    nargs="+",  # 1 or more positional arguments.

    help='arg_pos')

parser.add_argument(
    '-a', dest="arg_a", action='store',
    help="arg_a")

parser.add_argument(
    '-b', dest="arg_b", action='store',
    help="arg_b")

parser.add_argument(
    '-c', dest="arg_c", action='store',
    help="arg_c")

args = vars(parser.parse_args())


sys.stderr.write(f"args =\n{pformat(args)}\n")
