#!/usr/bin/env python
import os
import re
from typing import Union
import tpsup.uiatools
from pprint import pformat
import tpsup.sitetools
import tpsup.pstools

our_cfg = {
    'module': 'tpsup.uiatools',

    'position_args': [
        'action',
    ],

    # 'extra_args': {
    #     'explore': {'switches': ['-explore', '--explore'], 'action': 'store_true', 'default': False, 'help': "enter explore mode at the end of the steps"},
    # },

    'test_example': f'''
    ''',

    'usage_example': f'''
    examples:
        1. add putty pub keys to pageant.
            {{{{prog}}}} add
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
    debug = opt.get('debug', 0)
    action = opt['action']

    explore = opt.get('explore', 0)

    # yyyy, mm, dd = datetime.datetime.now().strftime("%Y,%m,%d").split(',')

    # steps = known['REMAININGARGS']

    # get program name
    caller = opt['caller']

    # remove .new, .old from caller
    caller = caller.split('.')[0]
    print(f'caller = {caller}')
    siteEnv = tpsup.sitetools.SiteEnv(caller)
    siteEnv.load_env(debug=debug)

    if action == 'add':
        # get siteenv command from env
        putty_key_files = siteEnv.get_env('putty_key_files')
        putty_key_passphrase = siteEnv.get_env('putty_key_passphrase')
        if not putty_key_files:
            raise Exception(f'putty_key_files not defined in site env {caller}')
        
        # check whether pageant.exe is already running
        pageant_running = tpsup.pstools.check_procs(['pageant.exe'])
        if pageant_running:
            print(f'pageant.exe is already running. "pkill.cmd pageant.exe" to stop it first.')
            exit(0)
        
        steps = [
            # start pageant with putty_key_files
            f'start=pageant.exe {putty_key_files}',

            # connect to pageant window
            'connect=title=Pageant',

            # input passphrase + Enter
            f'type={putty_key_passphrase}' + '{ENTER}',
        ]
    else:
        raise Exception(f'unknown action={action}, must be add')

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
