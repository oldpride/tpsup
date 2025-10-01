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
        'session_name',
        'instance_count',
    ],

    # 'extra_args': {
    #     'explore': {'switches': ['-explore', '--explore'], 'action': 'store_true', 'default': False, 'help': "enter explore mode at the end of the steps"},
    # },

    'test_example': f'''
    ''',

    'usage_example': f'''
    examples:
        1. test with session name wsl
            {{{{prog}}}} wsl 3
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

    session_name = opt['session_name']
    instance_count = opt['instance_count']
    explore = opt.get('explore', 0)

    # yyyy, mm, dd = datetime.datetime.now().strftime("%Y,%m,%d").split(',')

    # get program name
    caller = opt['caller']

    # remove .new, .old from caller
    caller = caller.split('.')[0]
    print(f'caller = {caller}')
    siteEnv = tpsup.sitetools.SiteEnv(caller)
    siteEnv.load_env(debug=debug)


    # get siteenv command from env
    siteenv_command = siteEnv.get_env('siteenv_command')
    print(f'siteenv_command={siteenv_command}')

    # steps = known['REMAININGARGS']
    steps = [
        f'start=putty -load {session_name}',

        # # wait for user to type ENTER to continue
        # 'readstdin=answer=hit ENTER to continue',

        # get the text from the putty window title
        'texts=titlevar',

        # normally only the first window of the same session has the original title 
        #    "... - PuTTY"
        # if we see it, it means the putty window is not yet "matured" waiting
        # for user to type the command to login.
        # we loop here until the title changes, meaning the putty window is "matured"
        # and ready for next command.
        'while=exp=titlevar[0].endswith(" - PuTTY")',
        'sleep=2',
        'texts=titlevar',
        'end_while',

        'sleep=1',
        f'type={siteenv_command}' + '{ENTER}',
        'sleep=2',

        # loop to open the rest instances without user interaction
        'python=i=1',
        f'while=exp=i<{instance_count}',
        f'start=putty -load {session_name}',
        f'type={siteenv_command}' + '{ENTER}',
        f'python=i=i+1',
        f'sleep=2',
        f'end_while',
        'type=paa{ENTER}',
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
