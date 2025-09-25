#!/usr/bin/env python
import os
import re
from typing import Union

import tpsup.uiatools
from pprint import pformat
import tpsup.sitetools

our_cfg = {
    'module': 'tpsup.uiatools',

    'position_args': [
        'instance_count',
    ],

    # 'extra_args': {
    #     'explore': {'switches': ['-explore', '--explore'], 'action': 'store_true', 'default': False, 'help': "enter explore mode at the end of the steps"},
    # },

    'test_example': f'''
    ''',

    'usage_example': f'''
    examples:
        {{{{prog}}}} 3
    ''',

    'show_progress': 1,

    'opt': {
        # 'humanlike': 1, # slow down a bit, more human-like
        # "browserArgs": ["--disable-notifications"],
    },
}

def code(all_cfg, known, **opt):
    # global driver

    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'from code(), known ={pformat(known)}')
        print(f'from code(), opt = {pformat(opt)}')

    dryrun = opt.get('dryrun', 0)
    run_js = opt.get('js', 0)
    trap = opt.get('trap', 0)
    debug = opt.get('debug', 0)

    instance_count = opt['instance_count']
    explore = opt.get('explore', 0)

    # yyyy, mm, dd = datetime.datetime.now().strftime("%Y,%m,%d").split(',')

    # get program name
    caller = opt['caller']

    # remove .new, .old from caller
    caller = caller.split('.')[0]
    print(f'caller = {caller}')
    siteEnv = tpsup.sitetools.SiteEnv()
    siteEnv.load_env(caller, debug=debug)

    # get siteenv command from env
    siteenv_command = siteEnv.get_env('siteenv_command')
    if not siteenv_command:
        raise RuntimeError("siteenv_command not set in site env file")

    # find where is cygwin mintty.exe
    cygwin_paths = [
        "C:/cygwin64/bin/mintty.exe",
        "C:/Program Files/cygwin64/bin/mintty.exe"
    ]

    mintty_path = None
    for p in cygwin_paths:
        if os.path.isfile(p):
            mintty_path = p
            break

    # steps = known['REMAININGARGS']
    steps = [
        
        'python=i=0',
        f'while=exp=i<{instance_count}',
        f'start={mintty_path} -i /Cygwin-Terminal.ico -title 123 -',
        f'sleep=2',
        f'type={siteenv_command}' + '{ENTER}',
        f'python=i=i+1',
        f'sleep=2',
        f'end_while',
    ]

    print(f'steps = [')
    for step in steps:
        # we print string without pformat to make js more readable.
        step_type = type(step)
        if step_type == str:
            print(f'    "{step}",')
        elif step_type == dict:
            print(f'    {pformat(step)},')
        else:
            raise Exception(f'unknown step type={step_type}')
    print(f']')

    driverEnv: tpsup.uiatools.UiaEnv = all_cfg["resources"]["uia"]['driverEnv']
    result = driverEnv.follow(steps, **opt)
    # if explore mode, enter explore mode at the end of the steps
    if explore:
        print("enter explore mode")
        driverEnv.explore(**opt)

def parse_input_sub(input: Union[str, list], all_cfg: dict, **opt):
    return {'REMAININGARGS': input}
