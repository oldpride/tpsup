#!/usr/bin/env python
import argparse
import os

from tpsup.tracer import parse_cfg, trace
from tpsup.exectools import exec_into_globals
from pprint import pformat
from tpsup.util import resolve_scalar_var_in_string
from tpsup.env import restore_posix_paths
import sys

prog = os.path.basename(sys.argv[0])

args = sys.argv[1:]  # shift

usage_str = ''

prog = os.path.basename(__file__)


def exec_simple(source):
    return exec_into_globals(source, globals(), locals())


def usage(message: str = None, **opt):
    if message is not None:
        print(message)

    usage_caller = None
    example_caller = None

    caller = opt.get('caller', None)
    all_cfg = opt.get('all_cfg', {})

    if caller:
        usage_caller = caller
        position_args = all_cfg.get('position_args', None)
        if position_args:
            usage_caller += ' ' + ' '.join(position_args)

        example_caller = caller
    else:
        usage_caller = f'{prog} cfg.py'
        example_caller = f'{prog} tptrace_test_cfg_trace.py'

    detail = all_cfg.get('usage_detail', "")
    example = all_cfg.get('usage_example', None)

    if detail:
        detail = resolve_scalar_var_in_string(detail, {'prog': usage_caller})

    if example is None:

        example = '''
    {{prog}} example=orders
    
    {{prog}} tid=123
    {{prog}} sec=IBM orderqty=26,700 yyyymmdd=20211129
    {{prog}} sec=IBM filledqty=400 client=xyz
    {{prog}} sec=IBM client=xyz orderqty=1,500 # test the customized clause

    {{prog}} -t actions orderid=ORD-0001
'''

    example = resolve_scalar_var_in_string(
        example, {'prog': example_caller})

    usage_top = all_cfg.get('usage_top', None)
    if not usage_top:
        usage_top = f'''
    {usage_caller} key1=value1  key2=value2 ...
    {usage_caller} ANY

    {detail}
    -v             verbose mode. each -v will increment level. eg -v -v, or -vv. max level is 2.


   the code flow is:
      xxx_script.py   -> tptrace.py -> tpsup.tracer ->    xxx_script_cfg_trace.py
   eg.
      tptrace_test.py -> tptrace.py -> tpsup.tracer ->  tptrace_test_cfg_trace.py 
'''
    print(f'''
    usage:
{usage_top}

example:
{example}

''', file=sys.stderr)
    exit(1)


# print(f'args = {args}')
# restore 'xpath=C:/Program Files/Git/html' back to 'xpath=/html'
args = restore_posix_paths(args)
# print(f'args = {args}')

if len(args) == 0:
    usage("missing args")

verbose = 0

if args[0] == '-v':
    verbose = verbose + 1
    args = args[1:]  # shift away -v
    if len(args) == 0:
        usage("missing args", caller=f'{prog} config.py')

config_file = args.pop(0)
all_cfg = parse_cfg(config_file)

printed_cfg = False
if verbose:
    print(f'all_cfg = {pformat(all_cfg)}')
    printed_cfg = True

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    # epilog=examples,
    # description=get_usage_str(usage_caller=f'{prog} config.py', detail=''),
    # formatter_class=argparse.RawTextHelpFormatter, # this honors \n but messed up indents
    formatter_class=argparse.RawDescriptionHelpFormatter
)

parser.add_argument(
    '-v', '--verbose', default=verbose, action="count",
    help='verbose level: -v, -vv, -vvv')

parser.add_argument(
    '-se', dest='SkipEntry', default=False, action="store_true",
    help='skip entry points')

parser.add_argument(
    '-f', dest='ForceThrough', default=False, action="store_true",
    help='force through even if error happens')

parser.add_argument(
    '-st', dest='SkipTraceString', default=None, action="store",
    help='skip tracing entities, eg, -st e1,e2')

parser.add_argument(
    '-t', dest='TraceString', default=None, action="store",
    help='only trace these entities, eg, -t e1,e2')

parser.add_argument(
    '-c', dest='caller', default=None, action="store",
    help='set the caller name')

parser.add_argument(
    # https://stackoverflow.com/questions/15583870
    # "argparse.REMAINDER" tells the argparse module to take the rest of the arguments in args,
    # when it finds the first argument it cannot match to the rest.
    'remainingArgs', nargs=argparse.REMAINDER,
    # this may not be desirable.
    # but the parser cannot handle intermixed options and positional args.
    help='app_cfg_trace.py and key=value pairs')

a = vars(parser.parse_args(args))

verbose = a.get('verbose', 0)
if verbose:
    if not printed_cfg:
        print(f'all_cfg = {pformat(all_cfg)}')
    print(f'a = {pformat(a)}')

if len(a['remainingArgs']) == 0:
    usage("missing positional args",
          caller=a.get('caller', None),
          all_cfg=all_cfg)

trace(all_cfg, a['remainingArgs'], **a)
