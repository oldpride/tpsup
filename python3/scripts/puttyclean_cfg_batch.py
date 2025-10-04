#!/usr/bin/env python
import os
import re
from typing import Union
import tpsup.uiatools
from pprint import pformat
import tpsup.sitetools

our_cfg = {
    'module': 'tpsup.uiatools',

    # 'position_args': [
    #     'session_name',
    #     'instance_count',
    # ],

    # 'extra_args': {
    #     'explore': {'switches': ['-explore', '--explore'], 'action': 'store_true', 'default': False, 'help': "enter explore mode at the end of the steps"},
    # },

    'test_example': f'''
    ''',

    'usage_example': f'''
    examples:
        1. remove all putty sessions with error popups.
            {{{{prog}}}} any
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

    explore = opt.get('explore', 0)

    # yyyy, mm, dd = datetime.datetime.now().strftime("%Y,%m,%d").split(',')

    # steps = known['REMAININGARGS']
    '''
    first locate the popup window whose title has 'Putty Error'.
    then locate the Close button of the popup, and click it.
    '''
    steps = [
        f'find=title_re=".*PuTTY.*Error.*" scope=desktop timeout=3 title2="OK" type2=Button action=click',
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
