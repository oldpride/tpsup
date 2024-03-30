#!/usr/bin/env python

import tpsup.cmdtools
from glob import glob
import os
import sys
import argparse
import textwrap
from pprint import pprint, pformat
from tpsup.logtools import get_logs_by_cfg


prog = os.path.basename(sys.argv[0]).replace('_cmd.py', '')
TwoDaysAgo = None

usage = textwrap.dedent("""
    usage:
        {prog} config.cfg id
                        
        get logs
                            
        'config.cfg' is the config file.
        id' is the id in the config file.

        -v                verbose mode

        -max INT          max number of logs

        -d yyyymmdd       default to today.

        -s separator      default to newline

        -b INT            backward these many days, ie, previous days.
    """)

TwoDaysAgo = tpsup.cmdtools.run_cmd('date -d "2 days ago" +%Y%m%d', is_bash=True)['stdout'].strip()

examples = textwrap.dedent(f"""
    examples:
                           
        {prog}        get_logs_test_cfg.py syslog
        {prog} -max 2 get_logs_test_cfg.py syslog
        
        {prog}        get_logs_test_cfg.py dpkg
        {prog} -max 2 get_logs_test_cfg.py dpkg

        {prog}                      get_logs_test_cfg.py lca
        {prog} -d {TwoDaysAgo}      get_logs_test_cfg.py lca
        {prog} -d {TwoDaysAgo} -b 3 get_logs_test_cfg.py lca

    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

parser.add_argument(
    # 'pattern', default=None, action='store', help='regex pattern')
    '-max', dest='LogLastCount', default=None, action="store", help='max number of logs')

parser.add_argument(
    '-d', dest='yyyymmdd', action="store",
    default=None, help='default to today')

parser.add_argument(
    '-s', dest='separator', action="store",
    default="\n", help='separator; default to newline')

parser.add_argument(
    '-b', dest='BackwardDays', action="store",
    default=None, help='backward these many days, ie, previous days')

parser.add_argument(
    '-v', dest='verbose', default=0, action="count",
    help='verbose mode. -v, -vv, -vvv, ...')

parser.add_argument(
    'cfg_and_id',
    # 0 or more positional arguments. can handle intermixed options and positional args.
    nargs='*',
    help='optionally additional files')

args = vars(parser.parse_args())

verbose = args['verbose']

if verbose:
    print(f'args={pformat(args)}', file=sys.stderr)

# check if we have the 2 required positional args
if len(args['cfg_and_id']) != 2:
    print(usage)
    print
    print(examples)
    sys.exit(1)
    # usage("missing positional args",
    #       caller=a.get('caller', None),
    #       all_cfg=all_cfg)


opt = {}

# pop out the first positional arg, which is the pattern
cfg_file, id = args['cfg_and_id']

get_logs_by_cfg(cfg_file, id, **args)
