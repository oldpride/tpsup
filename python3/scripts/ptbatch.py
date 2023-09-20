#!/usr/bin/env python
import argparse
import os

from tpsup.batch import parse_cfg, run_batch
from tpsup.exectools import exec_into_globals
from pprint import pformat
from tpsup.util import resolve_scalar_var_in_string
from tpsup.envtools import restore_posix_paths
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
        usage_caller = f'{prog} cfg.py pos_arg1 pos_arg2 ...'
        example_caller = f'{prog} cfg.py 192.168.1.179:9333'

    detail = all_cfg.get('usage_detail', "")
    example = all_cfg.get('usage_example', None)

    if detail:
        detail = resolve_scalar_var_in_string(detail, {'prog': usage_caller})

    if example:
        example = resolve_scalar_var_in_string(
            example, {'prog': example_caller})
    else:
        example = f'''
    on linux:
    linux$ {example_caller} q=python
    linux$ {example_caller} -batch ptslnm_test_batch.txt
    
    on windows, in gitbash an cygwin, the same as linux
    gitbash$ {example_caller} q=python
    gitbash$ {example_caller} q=python
    
    in cygwin is more complicated, needs to convert to cygpath. see ptslnm_test.py as example
    
'''

    extra_args_usage = ''
    extra_args = all_cfg.get('extra_args', [])

    # sort by key
    for k, v in sorted(extra_args.items()):
        print_type = ''
        if v.get('action', None) == 'store':
            v_type = v.get('type', None)
            if not v_type:
                print_type = 'str'
            else:
                print_type = v_type.__name__

        extra_args_usage += f'''
    {"|".join(v["switches"])} {print_type}   {v["help"]}
    '''

    usage_top = all_cfg.get('usage_top', None)
    if not usage_top:
        usage_top = f'''
    {usage_caller} key1=value1  key2=value2 ...
    {usage_caller} suit=suit1   key1=value1 ...
    {usage_caller} -batch fille key1=value1 ...
    {usage_caller} ANY

    {detail}
    -v             verbose mode. each -v will increment level. eg -v -v, or -vv. max level is 2.

    {extra_args_usage}
   'pos_arg' is required and defined in file.cfg

   If value is '-', it will take from STDIN. click 'Enter' then 'Control+D' to end.
   Only one '-' is allowed.

   'suit' is a set of pre-defined keys; can be overwritten by command-line key=value.

   the code flow is:
      linked_script.py -> ptbatch.py -> tpsup.batch ->    xxx_cfg.py file   -> module
   eg.
      ptslnm_test.py   -> ptbatch.py -> tpsup.batch ->   ptslnm_test_cfg.py -> tpsup.seleniumtools
'''
    print(f'''
    usage:
{usage_top}

example:
{example}

''', file=sys.stderr)
    exit(1)


if len(args) == 0:
    usage("missing args", caller=f'{prog} config.py')

verbose = 0

if args[0] == '-v':
    verbose = verbose + 1
    args = args[1:]  # shift away -v
    if len(args) == 0:
        usage("missing args", caller=f'{prog} config.py')

all_cfg = parse_cfg(args[0])
all_cfg['cfg_file'] = args[0]
if verbose:
    print(f'all_cfg = {pformat(all_cfg)}')

args = args[1:]  # shift away config.py

# print(f'args = {args}')
# restore 'xpath=C:/Program Files/Git/html' back to 'xpath=/html'
args = restore_posix_paths(args)
# print(f'args = {args}')

parsers = []

for i in range(2):
    parsers.append(argparse.ArgumentParser(
        prog=sys.argv[0],
        # epilog=examples,
        # description=get_usage_str(usage_caller=f'{prog} config.py', detail=''),
        # formatter_class=argparse.RawTextHelpFormatter, # this honors \n but messed up indents
        formatter_class=argparse.RawDescriptionHelpFormatter
    ))

# verbose is not moved into batch.py because its default value
# comes from here.
parsers[0].add_argument(
    '-v', '--verbose', default=verbose, action="count",
    help='verbose level: -v, -vv, -vvv')

parsers[1].add_argument(
    '-v', '--verbose', default=argparse.SUPPRESS, action="count",
    help='verbose level: -v, -vv, -vvv')

extra_args = all_cfg.get('extra_args', {})

for k, v in extra_args.items():
    # convert dict to **kwargs
    parser1 = parsers[0].add_argument(
        *v["switches"], **{k2: v2 for k2, v2 in v.items() if k2 != 'switches'}, dest=k
    )
    parser2 = parsers[1].add_argument(
        *v["switches"], **{k2: v2 for k2, v2 in v.items() if k2 != 'switches'}, dest=k
    )
    parser2.default = argparse.SUPPRESS

for i in range(2):
    parsers[i].add_argument(
        # args=argparse.REMAINDER indicates optional remaining args and stored in a List
        'remainingArgs', nargs=argparse.REMAINDER,
        help='remaining args. Can be mod_file if -modOnly set, or default to args to the preceding '
             'mod_file, start with --')

# catch-22
# parse_args() cannot handle intermixed args
# a = vars(parser.parse_args(args))
#
# as of python 3.10, 2022/04/10, parse_intermixed_args() cannot handle nargs
# a = vars(parser.parse_intermixed_args(args))
#
# therefore, we have to design a loop
#
# but this loop has a problem, some args are parsed in the first round and get user setting.
# in the 2nd round, they are reverted to default.
# therefore, we have to create two parsers.
#     - parsers[0] is like standard parser
#     - parsers[1] has default = argparse.SUPPRESS, meaning it will not show up in result dict if
#       user not set. this prevents the overwrite.

saved = {}
# verbose is additive, therefore, we need to keep track of it
saved['verbose'] = verbose

remainingArgs = []
a = {}
round = 1
while args:
    parser = None
    if round == 1:
        parser = parsers[0]
    else:
        parser = parsers[1]

    # all command-line switches now go from 'extra_args' to 'adict'
    adict = vars(parser.parse_args(args))
    if verbose:
        print(f'parse cmd line round {round}, adict={pformat(adict)}')
    round = round+1
    remainings = adict['remainingArgs']
    adict.pop('remainingArgs')   # delete the key from dict

    # all command-line switches now go from 'adict' to 'a'
    a.update(adict)

    if 'verbose' in adict:
        # verbose is additive, we treat it differently
        if verbose:
            print(
                f"saved['verbose'] = {saved['verbose']},  adict['verbose']={adict['verbose']}")
        saved['verbose'] += adict['verbose']
    a.update(saved)

    if remainings:
        remainingArgs.append(remainings[0])
        args = remainings[1:]
    else:
        args = remainings  # this is empty

verbose = saved['verbose']
if verbose:
    print(f"a = {pformat(a)}")

position_args = all_cfg.get('position_args', [])

opt = {}

caller = a['caller']

# if verbose:
#     print(f'remainingArgs = {remainingArgs}')
#     # exit
#     exit(0)

if (len(position_args) > len(remainingArgs)):
    usage(f'missing positional args, expecting {len(position_args)}, '
          f'actual {len(remainingArgs)}', caller=caller, all_cfg=all_cfg)
for pa in position_args:
    opt[pa] = remainingArgs[0]
    remainingArgs = remainingArgs[1:]  # shift

# the goal is to print usage when user provides no args.
# if we have required position args, we don't require remaining args.
# minimal_args is the number of remaining args
if position_args:
    minimal_args = all_cfg.get('minimal_args', 0)
else:
    minimal_args = all_cfg.get('minimal_args', 1)

batch = a['batch']
if len(remainingArgs) < minimal_args and batch is None:
    usage(f'missing args, expecting {minimal_args}, '
          f'actual {len(remainingArgs)}', caller=caller, all_cfg=all_cfg)

a.pop('batch')  # remove batch from a

# all command-line switches now go from 'a' to 'opt'
opt.update(a)

# we can use command-line switches (now in 'opt') to override default values in all_cfg.
# we couldn't have done it in parse_cfg() because
#    1. we need all_cfg's extra_args to parse command-line switches.
#    2. all_cfg's extra_args are not available until after parse_cfg().
# therefore, we do the override here.
for k in all_cfg.keys():
    cmdline_value = opt.get(k, None)
    if cmdline_value is not None:
        print("", file=sys.stderr)
        print(
            f"overriding {k} from '{all_cfg[k]}' to '{cmdline_value}'", file=sys.stderr)
        all_cfg[k] = cmdline_value
# the override waterfall is:
#   1. command-line switches
#   2. app_cfg.py
#   3. module.py
#   4. batch.py
# after the above steps, all overrides are done !!! final values are in all_cfg.
# override logic of steps 2, 3, 4 were done in parse_cfg().

if verbose:
    print(f'opt={pformat(opt)}')
    print(f'remainingArgs={remainingArgs}')

if batch is not None:
    run_batch(all_cfg, batch, **opt)
else:
    run_batch(all_cfg, [remainingArgs], **opt)
