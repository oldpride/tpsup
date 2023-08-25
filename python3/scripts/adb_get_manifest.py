#!/usr/bin/env python

import os
import sys
import argparse
import textwrap
from pprint import pprint, pformat
from tpsup.androidtools import get_app_manifest

prog = os.path.basename(sys.argv[0])

usage = textwrap.dedent("""
    get app manifest using adb.
    this assumes adb is already connected to the device or emulator.
    """)

examples = textwrap.dedent(f"""
    examples:
    {prog} gallery
    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

parser.add_argument(
    'app_pattern', default=None, action='store',
    help='app pattern, eg, gallery, case insensitive')

parser.add_argument(
    '-v', '--verbose', default=0, action="count",
    help='verbose level: -v, -vv, -vvv')

args = vars(parser.parse_args())

if args['verbose'] > 0:
    print(f'args =\n{pformat(args)}')

content = get_app_manifest(args['app_pattern'], **args)
print(content)
