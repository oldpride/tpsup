#!/usr/bin/env python

from pprint import pformat
import tpsup.pstools
import tpsup.env
import tpsup.dummytools

start_number = 0
testfile = tpsup.tptmp.tptmp().get_dailylog()
with open(testfile, 'w') as ofh:
    ofh.write(f'{start_number}\n')

our_cfg = {

    'resources': {
        'dummyDriver': {
            'method': tpsup.dummytools.get_driver,
            'cfg': {'arg1' :3}, # will be overriden by extra_args, which is from command line.
            "init_resource": 0,  # delay init until first use
        },
    },

    'position_args': ['input_retry'],

    'extra_args': [
        {'dest': 'input_retry_reset', 'default': 1, 'type': int,
            'action': 'store', 'help': 'reset driver before retry input, default 1'},
        {'dest': 'arg1', 'default': 5, 'type': int,
            'action': 'store', 'help': 'arg1, default 5'},
    ],

    "keys": {
        "target": 2,
    },

    "aliases": {"t": "target"},

    'usage_example': '''

    # retry 2 times
    {{prog}} 2 target=0
    {{prog}} 2 target=1
    {{prog}} 2 target=2
    {{prog}} 2 target=3
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

    driver = all_cfg["resources"]["dummyDriver"]['driver']
    print(f'driver = {pformat(driver)}')

    target = int(known['TARGET'])

    current_number = None
    with open(testfile, 'r') as ifh:
        current_number = int(ifh.read().strip())
    print

    if current_number >= target:
        print(
            f'current_number {current_number} >= target {target}, Good. exit')
        return 0

    with open(testfile, 'w') as ofh:
        ofh.write(f'{current_number + 1}\n')

    raise Exception(
        f'current_number {current_number} < target {target}, raise exception.')


def pre_batch(all_cfg, **opt):  # known is not available to pre_batch()
    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'calling pre_batch()')
    if not 'driver' in all_cfg["resources"]["dummyDriver"]:
        print('we start driver at a delayed time')
        method = all_cfg["resources"]["dummyDriver"]["driver_call"]['method']
        kwargs = all_cfg["resources"]["dummyDriver"]["driver_call"]["kwargs"]
        all_cfg["resources"]["dummyDriver"]['driver'] = method(**kwargs)


def post_batch(all_cfg, known, **opt):
    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'calling post_batch()')
    if 'driver' in all_cfg["resources"]["dummyDriver"]:
        all_cfg["resources"]["dummyDriver"]["driver"] = None
        # delete driver so that it will be re-created next time.
        all_cfg["resources"]["dummyDriver"].pop('driver')
