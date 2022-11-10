#!/usr/bin/env python

#!/usr/bin/env python

import argparse
import sys
import textwrap
from pprint import pformat
# from inspect import currentframe, getframeinfo
import os

prog = os.path.basename(sys.argv[0])


# https://docs.python.o
def main():
    usage = textwrap.dedent(""""
        find python module path
        """)

    examples = textwrap.dedent(f""" 
    examples:
        {prog} os
        {prog} pyautogui
        """)

    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description=usage,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples)

    parser.add_argument(
        'module',
        help="module name")

    parser.add_argument(
        '-v', '--verbose', default=0, action="count",
        help='verbose level: -v, -vv, -vvv')

    args = vars(parser.parse_args())

    verbose = args['verbose']
    module = args['module']

    if verbose:
        sys.stderr.write(f"args =\n{pformat(args)}\n")

    imported = __import__(module)
    print(f'path={imported.__file__}')
    print(f'version={imported.__version__}')


if __name__ == '__main__':
    main()
