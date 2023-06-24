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
        'selenium': {
            'method': tpsup.dummytools.get_driver,
            'cfg': {},
            "init_resource": 0,
        },
    },

    'position_args': ['input_retry'],

    # 'extra_args': [
    #     {'dest': 's', 'start': 0, 'type': int,
    #         'action': 'store', 'help': 'set start number, default is 0'},
    # ],

    "keys": {
        "target": 2,
    },

    "aliases": {"t": "target"},

    'usage_example': '''
    {{prog}} 2 t=0
    {{prog}} 2 t=1
    {{prog}} 2 t=2
    {{prog}} 2 t=3
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


def post_batch(all_cfg, known, **opt):
    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'calling post_code()')
