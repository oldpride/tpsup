#!/usr/bin/env python

from pprint import pformat
import tpsup.pstools
import tpsup.envtools
import tpsup.dummytools

start_number = 0
testfile = tpsup.tptmp.tptmp().get_dailylog()
with open(testfile, 'w') as ofh:
    ofh.write(f'{start_number}\n')

our_cfg = {

    'resources': {
        'dummy': {
            'method': tpsup.dummytools.get_driver,
            # will be overriden by extra_args, which is from command line.
            'cfg': {'arg1': 3},
            "init_resource": 0,  # delay init until first use
        },
    },

    'module': 'tpsup.dummytools',

    # 'position_args': ['input_retry'],

    'extra_args': {
        'arg1': {'switches': ['--arg1'], 'default': 5, 'type': int,
                 'action': 'store', 'help': 'arg1, default 5'},
    },

    "keys": {
        "target": 2,
    },

    "aliases": {"t": "target"},

    'usage_example': '''

    # retry 2 times
    {{prog}} --retry 2 target=0  # success with 1st try
    {{prog}} --retry 2 target=1  # success with 2nd try - 1st retry
    {{prog}} --retry 2 target=2  # success with 3rd try - 2nd retry
    {{prog}} --retry 2 target=3  # fail with 3rd try - 2nd retry
    ''',

    'show_progress': 1,
}


def code(all_cfg, known, **opt):
    # **opt combines all_cfg['opt'] and command line args.
    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'''
from code(), known =
{pformat(known)}

from code(), opt =
{pformat(opt)}

''')

    driver = all_cfg["resources"]["dummy"]['driver']
    print(f'driver = {pformat(driver)}')

    target = int(known['TARGET'])

    current_number = None
    with open(testfile, 'r') as ifh:
        current_number = int(ifh.read().strip())

    print(f'current_number = {current_number}')

    if current_number >= target:
        print(
            f'current_number {current_number} >= target {target}, Good. exit')
        return 0

    with open(testfile, 'w') as ofh:
        ofh.write(f'{current_number + 1}\n')

    raise Exception(
        f'current_number {current_number} < target {target}, raise exception.')
