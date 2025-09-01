#!/usr/bin/env python
import os
import re
from typing import Union

import tpsup.envtools
import tpsup.csvtools
import tpsup.htmltools
import tpsup.seleniumtools_new
import tpsup.locatetools_new
import tpsup.pstools
from pprint import pformat

HOME = tpsup.envtools.get_home_dir()
TPSUP = os.environ['TPSUP']

# convert to native path, eg, /cygdrive/c/User/tian/... to C:/User/tian/...
TPSUP = tpsup.envtools.convert_path(TPSUP)

TPP3 = f'{TPSUP}/python3/scripts'

our_cfg = {
    'module': 'tpsup.pwatools',

    # 'position_args': [
    #     # 'url'
    # ],

    # 'extra_args': {
    # },

    'test_example': f'''
    ''',

    'usage_example': f'''

    - notepad example.
    notepad on windows 11 spawns a new process after start, therefore, we need a connect step.
    {{{{prog}}}} start="notepad.exe tianjunk" connect="title_re=.*tianjunk.*" 

    - putty example,
    {{{{prog}}}} start="putty -load wsl" type="pwd{{ENTER}}"
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

def pre_batch(all_cfg, known, **opt):
    # run tpsup.seleniumtools.pre_batch() to set up driver
    tpsup.seleniumtools_new.pre_batch(all_cfg, known, **opt)

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

    # yyyy, mm, dd = datetime.datetime.now().strftime("%Y,%m,%d").split(',')

    steps = []

    locator_chain = known['REMAININGARGS']

    # moved below to seleniumtools
    # locator_chain = []
    # for locator in known['REMAININGARGS']:
    #     # gitbash changes xpath=/html/body to xpath=C:/Program Files/Git/html/body
    #     # so we need to change it back
    #     locator2 = re.sub(r'xpath=C:/Program Files/Git', 'xpath=', locator, flags=re.IGNORECASE|re.DOTALL)
    #     if locator2 != locator:
    #         print(f'corrected locator from {locator} to {locator2}')
    #     locator_chain.append(locator2)

    if run_js:
        locator_chain2 = tpsup.seleniumtools_new.locator_chain_to_locator_chain_using_js(locator_chain, trap=trap, debug=debug)
        steps.extend(locator_chain2)
    else:
        steps.extend(locator_chain)

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

    # result = tpsup.seleniumtools.check_syntax_then_follow(steps, **opt)
    driverEnv: tpsup.seleniumtools_new.SeleniumEnv = all_cfg["resources"]["selenium"]['driverEnv']
    followEnv = tpsup.locatetools_new.FollowEnv(driverEnv.locate, **opt)
    result = followEnv.follow(steps, **opt)

def parse_input_sub(input: Union[str, list], all_cfg: dict, **opt):
    caller = all_cfg.get('caller', None)

    # if user enter 'example', then we print out usage_example and quit
    if re.match(r'example$', input[0]):
        print(all_cfg.get('usage_example', '').replace("{{prog}}", caller))
        exit(0)

    if re.match(r'(file_example|fe)$', input[0]):
        print(all_cfg.get('usage_example', '').replace("{{prog}}", f'{caller} -af').replace(HTTP_BASE, FILE_BASE))
        exit(0)
    
    if re.match(r'^(test|test_example)$', input[0]):
        print(all_cfg.get('test_example', '').replace("{{prog}}", caller))
        exit(0)

    if re.match(r'(file_test|ft)$', input[0]):
        print(all_cfg.get('test_example', '').replace("{{prog}}", f'{caller} -af').replace(HTTP_BASE, FILE_BASE))
        exit(0)

    # if re.match(r'locators$', input[0]):
    #     for line in tpsup.locatetools_new.decoded_get_defined_locators(locate_func=tpsup.seleniumtools_new.locate_f):
    #         print(line)
    #     exit(0)

    if re.match(r'(d|download_chrome)driver$', input[0]):
        version = input[1] if len(input) > 1 else None
        tpsup.seleniumtools_new.download_chromedriver(driver_version=version)
        exit(0)

    if re.match(r'check_setup$', input[0]):
        tpsup.seleniumtools_new.check_setup(compareVersion=1)
        exit(0)

    return {'REMAININGARGS': input}
