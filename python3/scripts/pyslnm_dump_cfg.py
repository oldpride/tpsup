#!/usr/bin/env python
import datetime
import os
import time
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
    'position_args' : ['host_port', 'url', 'dir'],

    'extra_args' : [
        # argparse's args
        {
            'dest' : 'headless',
            'default' : False,
            'action' : 'store_true',
            'help' : 'run in headless mode'
        },
        {
            'dest' : 'xpath',
            'default' : None,
            'action' : 'store',
            'help' : 'specify a xpath'
        },
    ],

    'usage_example' : '''
    - this will dump out dynamically generated html too
    
    note: 
        as of 2022/09/04
        https://www.google.com and https://google.com are the same in the Chrome browser: no iframe nor shadow.
        however, Chrome's new tab default to a search page lookalike: has both iframes and shadow.
    {{prog}} auto https://www.google.com ~/dumpdir -np
    {{prog}} auto https://www.google.com %USERPROFILE%/dumpdir -np kqq
    {{prog}} auto chrome-search://local-ntp/local-ntp.html %USERPROFILE%/dumpdir -np # this is the new tab url
    
    - has shadows, no iframes, simple pages to test shadows
    {{prog}} auto https://iltacon2022.expofp.com %USERPROFILE%/dumpdir -np
    {{prog}} auto http://watir.com/examples/shadow_dom.html %USERPROFILE%/dumpdir -np
    
    - has both iframes and shadows
    {{prog}} auto https://www.dice.com %USERPROFILE%/dumpdir -np
    
    - xpath, from cmd.exe
    {{prog}} auto https://iltacon2022.expofp.com %USERPROFILE%/dumpdir -np -xpath //div[@class=\\"expofp-floorplan\\"]
    
    - to test deep-nested shadow
    {{prog}} auto chrome://settings %USERPROFILE%/dumpdir -np
    
    ''',

    'show_progress': 1,

    'opt' : {
        # 'humanlike': 1, # slow down a bit, more human-like
        # "browserArgs": ["--disable-notifications"],
    },
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
    dir = opt.get('dir')
    xpath = opt.get('xpath')

    yyyy, mm, dd = datetime.datetime.now().strftime("%Y,%m,%d").split(',')
    os.makedirs(dir, exist_ok=True) # this does "mkdir -p"

    if driver is None:
        method = all_cfg["resources"]["selenium"]["driver_call"]['method']
        kwargs = all_cfg["resources"]["selenium"]["driver_call"]["kwargs"]
        driver = method(**{**kwargs, "dryrun":0}) # overwrite kwargs

    actions = [
        [f'url={url}', 'sleep=2', 'go to url'],
    ]

    if xpath:
        actions.append([f'xpath={xpath}', f'dump_element={dir}', f'dump {xpath} to {dir}'])
    else:
        actions.append([None, f'dump_all={dir}', f'dump all to {dir}'])

    print(f'actions = {pformat(actions)}')
    result = tpsup.seleniumtools.run_actions(driver, actions, **{**opt, 'dryrun':0})

def post_batch(all_cfg, known, **opt):
    global driver
    print(f'running post batch')
    driver.quit()
    if tpsup.pstools.prog_running('chrome', printOutput=1):
        print(f"seeing leftover chrome")
