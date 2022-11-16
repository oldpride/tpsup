#!/usr/bin/env python
import datetime
import os
import time
from typing import Union

import tpsup.env
import json
import tpsup.csvtools
import tpsup.htmltools
import tpsup.appiumtools
import tpsup.pstools
from pprint import pformat
# from selenium import webdriver
from appium import webdriver


our_cfg = {
    'resources': {
        'appium' : {
            'method': tpsup.appiumtools.get_driver,
            'cfg': {
                # 'host_port': 'auto'
            },
            'init_resource': 0, # we delay the driver init till we really need it.
        },
    },

    # appiumEnv = AppiumEnv(adb_devicename='emulator-5558', host_port='localhost:4723', is_emulator=True)

    # position_args will be inserted into $opt hash to pass forward
    'position_args' : ['adb_devicename', 'host_port', 'output_dir'],

    'extra_args' : [
        # argparse's args
        {
            'dest' : 'headless',
            'default' : False,
            'action' : 'store_true',
            'help' : 'run in headless mode',
        },
        {
            'dest' : 'is_emulator',
            'default' : False,
            'action' : 'store_true',
            'help' : 'this is emulator, therefore, auto start it if it is not running',
        },
        {
            'dest' : 'js',
            'default' : False,
            'action' : 'store_true',
            'help' : 'run js'
        },
        {
            'dest' : 'trap',
            'default' : False,
            'action' : 'store_true',
            'help' : 'used with -js, to add try{...}catch{...}',
        },
        {
            'dest' : 'full',
            'default' : False,
            'action' : 'store_true',
            'help' : 'print full xpath in levels, not shortcut, eg. /html/body/... vs id("myinput")',
        },
        {
            'dest' : 'print_console_log',
            'default' : False,
            'action' : 'store_true',
            'help' : 'print js console log',
        },
        {
            'dest': 'limit_depth',
            'default': 5,
            'action': 'store',
            'type': int,
            'help': 'limit scan depth',
        },
    ],

    'usage_example' : f'''
    - test a static page with nested iframes, same origin
    {{{{prog}}}} emulator-5558 localhost:4723 %USERPROFILE%/dumpdir2 --is_emulator 
    ''',

    'show_progress': 1,

    'opt' : {
        # 'humanlike': 1, # slow down a bit, more human-like
        # "browserArgs": ["--disable-notifications"],
    },
}

def code(all_cfg, known, **opt):

    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'from code(), known ={pformat(known)}')
        print(f'from code(), opt = {pformat(opt)}')

    dryrun = opt.get('dryrun', 0)
    url = opt.get('url')
    output_dir = opt.get('output_dir')
    run_js = opt.get('js', 0)
    trap = opt.get('trap', 0)

    yyyy, mm, dd = datetime.datetime.now().strftime("%Y,%m,%d").split(',')
    os.makedirs(output_dir, exist_ok=True) # this does "mkdir -p"

    driver: webdriver = all_cfg["resources"]["appium"].get("driver", None)
    if driver is None:
        method = all_cfg["resources"]["appium"]["driver_call"]['method']
        kwargs = all_cfg["resources"]["appium"]["driver_call"]["kwargs"]
        driver = method(**{**kwargs, "dryrun":0}) # overwrite kwargs
        all_cfg["resources"]["appium"]["driver"] = driver

    actions = []

    locator_chain = known['REMAININGARGS']
    if run_js:
        # js_list = tpsup.seleniumtools.locator_chain_to_js_list(locator_chain, trap=trap)
        # locator_chain2 = tpsup.seleniumtools.js_list_to_locator_chain(js_list)
        # actions.append([locator_chain2, f'dump_element={output_dir}', f'dump element to {output_dir}'])
        pass
    else:
        actions.append([locator_chain, f'dump_element={output_dir}', f'dump element to {output_dir}'])

    print(f'actions = {pformat(actions)}')
    # result = tpsup.seleniumtools.run_actions(driver, actions, **opt)

def parse_input_sub(input: Union[str, list], all_cfg: dict, **opt):
    return { 'REMAININGARGS' : input }

def post_batch(all_cfg, known, **opt):
    print(f'running post batch')
    driver: webdriver = all_cfg["resources"]["appium"].get("driver", None)
    if driver:
        print('driver.quit()')
        driver.quit()
    else:
        print("driver didn't start.")

    if tpsup.pstools.prog_running('chromed', printOutput=1):
        print(f"seeing leftover chrome")
