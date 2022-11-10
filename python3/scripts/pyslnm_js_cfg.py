#!/usr/bin/env python
import datetime
import glob
import os
import time
from typing import Union

import tpsup.env
import json
import tpsup.csvtools
import tpsup.htmltools
import tpsup.seleniumtools
import tpsup.pstools
from pprint import pformat
from selenium import webdriver


our_cfg = {

    'resources': {
        'selenium' : {
            'method': tpsup.seleniumtools.get_driver,
            'cfg': {
                # 'host_port': 'auto'
            },
            'init_resource': 0, # we delay the driver init till we really need it.
        },
    },

    # position_args will be inserted into $opt hash to pass forward
    'position_args' : ['host_port', 'url'],

    'extra_args' : [
        # argparse's args
        {
            'dest' : 'headless',
            'default' : False,
            'action' : 'store_true',
            'help' : 'run in headless mode',
        },
        {
            'dest' : 'trap',
            'default' : False,
            'action' : 'store_true',
            'help' : 'add try{...}catch{...}',
        },
    ],

    'usage_example' : '''
    - run java script
    
    from cmd.exe
    {{prog}} auto chrome-search://local-ntp/local-ntp.html "%TPSUP%"\\python3\\scripts\\locator_chain_test*.js

    from bash
    {{prog}} auto chrome-search://local-ntp/local-ntp.html "$TPSUP"/python3/scripts/locator_chain_test*.js 
    ''',

    'show_progress': 1,
}

driver: webdriver.Chrome = None # we define this globally so that post_code() can use it too

def code(all_cfg, known, **opt):
    global driver

    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'from code(), known ={pformat(known)}')
        print(f'from code(), opt = {pformat(opt)}')

    dryrun = opt.get('dryrun', 0)
    url = opt.get('url')
    trap = opt.get('trap', 0)

    if driver is None:
        method = all_cfg["resources"]["selenium"]["driver_call"]['method']
        kwargs = all_cfg["resources"]["selenium"]["driver_call"]["kwargs"]
        driver = method(**{**kwargs, "dryrun":0}) # overwrite kwargs

    actions = [
        [f'url={url}', 'sleep=2', 'go to url'],
        # [None, f'js={js_script}', 'run java_script'],
    ]

    i = 0
    # on Windows file*.js doesn't expand on cmd.exe. we have to expand it ourselves
    for js_pattern in known['REMAININGARGS']:
        for js_file in glob.glob(js_pattern):
            i += 1
            with open(js_file, 'r') as ifh:
                js = ifh.read()
                ifh.close()
                if trap:
                    js = tpsup.seleniumtools.wrap_js_in_trap(js)
                actions.append([f'js={js}', None,  f'run #{i} file {js_file}'])

    print(f'actions = {pformat(actions)}')
    result = tpsup.seleniumtools.run_actions(driver, actions, **opt)

    print(f"result element = {result['element'].get_attribute('outerHTML')}")
    tpsup.seleniumtools.js_print_debug(driver, result['element'])

def parse_input_sub(input: Union[str, list], all_cfg: dict, **opt):
    return { 'REMAININGARGS' : input }

def post_batch(all_cfg, known, **opt):
    global driver
    print(f'running post batch')
    driver.quit()
    if tpsup.pstools.prog_running('chromed', printOutput=1):
        print(f"seeing leftover chrome")
