#!/usr/bin/env python
import os
import re
from typing import Union

import tpsup.envtools
import tpsup.csvtools
import tpsup.htmltools
import tpsup.pwatools
import tpsup.locatetools_new
import tpsup.pstools
from pprint import pformat

HOME = tpsup.envtools.get_home_dir()
TPSUP = os.environ['TPSUP']

# convert to native path, eg, /cygdrive/c/User/tian/... to C:/User/tian/...
TPSUP = tpsup.envtools.convert_path(TPSUP)

TPP3 = f'{TPSUP}/python3/scripts'
HTTP_BASE = 'http://localhost:8000'
FILE_BASE = f'file:///{TPP3}'
EXAMPLE_BASE = HTTP_BASE

our_cfg = {
    'module': 'tpsup.pwatools',

    # 'position_args': [
    #     # 'url'
    # ],

    'extra_args': {
        'explore': {'switches': ['-explore', '--explore'], 'action': 'store_true', 'default': False, 'help': "enter explore mode at the end of the steps"},
    },

    'test_example': f'''
    ''',

    'usage_example': f'''
    examples:
        1: test notepad
            {{{{prog}}}} start="notepad c:/users/tian/tianjunk" connect="title_re=.*tianjunk.*"
            {{{{prog}}}} connect="title_re=.*tianjunk.*" -explore

        2: test putty
            {{{{prog}}}} start="putty -load wsl" "type=siteenv{{ENTER}}"
            {{{{prog}}}} start="putty -load wsl" "type=siteenv{{ENTER}}" -explore

    notes for windows cmd.exe, 
        double quotes cannot be escaped, 
        single quote is just a letter, cannot do grouping. 
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

    allowFile = opt.get('allowFile', 0)
    explore = opt.get('explore', 0)

    # yyyy, mm, dd = datetime.datetime.now().strftime("%Y,%m,%d").split(',')

    steps = known['REMAININGARGS']

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

    driverEnv: tpsup.pwatools.PwaEnv = all_cfg["resources"]["pwa"]['driverEnv']
    locateEnv = tpsup.locatetools_new.LocateEnv(
        locate_f=driverEnv.locate, 
        locate_usage=driverEnv.locate_usage_by_cmd,
        display_f=driverEnv.display_f,
        **opt)
    result = locateEnv.follow(steps, **opt)
    # if explore mode, enter explore mode at the end of the steps
    if explore:
        print("enter explore mode")
        locateEnv.explore(**opt)

def parse_input_sub(input: Union[str, list], all_cfg: dict, **opt):
    return {'REMAININGARGS': input}
