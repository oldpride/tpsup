#!/usr/bin/env python
import datetime
import os
import shutil
import time
from typing import Union

import tpsup.envtools
import json
import tpsup.csvtools
import tpsup.htmltools
import tpsup.seleniumtools
import tpsup.pstools
from pprint import pformat
from selenium import webdriver

HOME = tpsup.envtools.get_home_dir()
TPSUP = os.environ['TPSUP']

our_cfg = {
    'module': 'tpsup.seleniumtools',

    'position_args': ['url', 'output_dir'],

    'extra_args': {
        'js': {'switches': ['-js', '--js'],
               'default': False,
               'action': 'store_true',
               'help': 'run js'
               },
        'trap': {
            'switches': ['-trap', '--trap'],
            'default': False,
            'action': 'store_true',
            'help': 'used with -js, to add try{...}catch{...}',
        },
        'full': {
            'switches': ['-full', '--full'],
            'default': False,
            'action': 'store_true',
            'help': 'print full xpath in levels, not shortcut, eg. /html/body/... vs id("myinput")',
        },
        'print_console_log': {
            'switches': ['-ps', '--print_console_log'],
            'default': False,
            'action': 'store_true',
            'help': 'print js console log',
        },
        'limit_depth': {
            'switches': ['--limit_depth'],
            'default': 5,
            'action': 'store',
            'type': int,
            'help': 'limit scan depth',
        },
        'rm': {
            # remove the output directory before start
            'switches': ['-rm', '--rm'],
            'default': False,
            'action': 'store_true',
            'help': 'remove the output directory before start',
        },
        'dump_element': {
            # default is dump_all
            'switches': ['-de', '--dump_element'],
            'default': False,
            'action': 'store_true',
            'help': 'dump the element only',
        }
    },

    'usage_example': f'''

    - test a static page with nested iframes, same origin
    {{{{prog}}}} "file:///{TPSUP}/python3/scripts/iframe_over_shadow_test_main.html" "{HOME}/dumpdir2" xpath=//iframe[1] iframe xpath=//iframe[1] iframe xpath=//h1[1]  -js
    {{{{prog}}}} "file:///{TPSUP}/python3/scripts/iframe_over_shadow_test_main.html" "{HOME}/dumpdir2" xpath=//iframe[1] iframe xpath=//iframe[1] iframe xpath=//h1[1]
    
    - test a static page with nested iframes, cross origin (has dice.com iframe)
    {{{{prog}}}} "file:///{TPSUP}/python3/scripts/iframe_test1.html" "{HOME}/dumpdir2" xpath=//iframe[1] iframe xpath=//iframe[2] iframe xpath=//div[1]  -js
    {{{{prog}}}} "file:///{TPSUP}/python3/scripts/iframe_test1.html" "{HOME}/dumpdir2" xpath=//iframe[1] iframe xpath=//iframe[2] iframe xpath=//div[1]
    
    - this will dump out dynamically generated html too
      note:
        - add sleep time to let the page fully loaded.
               for local test page, this is not needed;
               but for remote page, this is needed. otherwise, you get error: 
               stale element reference: element is not attached to the page document
        - once entered shadow, xpath is not working anymore., use css selector instead.
    {{{{prog}}}} chrome-search://local-ntp/local-ntp.html "{HOME}/dumpdir2" "code=time.sleep(2)" xpath=/html/body/ntp-app shadow css=ntp-realbox shadow css=input 
    
    
    # iframe001: id("backgroundImage")
    # shadow001: /html[@class="focus-outline-visible"]/body[1]/ntp-app[1]
    # shadow001.shadow002: /div[@id="content"]/ntp-iframe[@id="oneGoogleBar"]
    # shadow001.shadow002.iframe002: /iframe[@id="iframe"]
    # div.gb_Id     # <div class="gb_Id">Google apps</div>

    # in shadow, we can only use css selector to locate
    # but once in iframe, even if an iframe inside an shadow root, we can use xpath again.
    
    # from cmd.exe, 
    #   double quotes cannot be escaped, 
    #   single quote is just a letter, cannot do grouping. 
    # therefore, xpath=//div[@class="gb_Id"] will not work on cmd.exe
    {{{{prog}}}} chrome-search://local-ntp/local-ntp.html "{HOME}/dumpdir2" xpath=/html/body/ntp-app shadow css=ntp-iframe shadow "css=#iframe" iframe xpath=//div[3]
    
    # from bash
    {{{{prog}}}} chrome-search://local-ntp/local-ntp.html ~/dumpdir2 xpath=/html/body/ntp-app shadow css=ntp-iframe shadow "css=#iframe" iframe 'xpath=//div[@class="gb_Id"]'

    # use -js
    {{{{prog}}}} chrome-search://local-ntp/local-ntp.html "{HOME}/dumpdir2" xpath=/html/body/ntp-app shadow css=ntp-iframe shadow "css=#iframe" iframe xpath=//div[3] -js
    
    {{{{prog}}}} chrome-untrusted://new-tab-page/one-google-bar?paramsencoded= "{HOME}/dumpdir2" xpath=//div[3] -js
    
    # test a cross domain iframe
    {{{{prog}}}} https://www.dice.com "{HOME}/dumpdir2" xpath=//iframe[4] iframe xpath=//script[1]
    {{{{prog}}}} https://www.dice.com "{HOME}/dumpdir2" xpath=//iframe[4] iframe xpath=//script[1] -js
    
    # dump whole page, print xpath shortcut, eg id("mycontainer")
    {{{{prog}}}} chrome-search://local-ntp/local-ntp.html "{HOME}/dumpdir2" xpath=/html
    
    # dump whole page, print full xpath
    {{{{prog}}}} chrome-search://local-ntp/local-ntp.html "{HOME}/dumpdir2" xpath=/html -full

    # dump whole page to find target locator chain and then dump nested shadow
    1. dump the whole page
    {{{{prog}}}} "file:///{TPSUP}/python3/scripts/ptslnm_locate_test_shadow.html" "{HOME}/dumpdir2"
    
    2. in dumpdir2/locator_chain_map.txt, find the locator chain for the target element
    shadow001.shadow002.shadow003: "xpath=id('div1')" "shadow" "css=#div2" "shadow" "css=#div3" "shadow"
    
    3. use the locator chain to dump the target element
    {{{{prog}}}} "file:///{TPSUP}/python3/scripts/ptslnm_locate_test_shadow.html" "{HOME}/dumpdir2" "xpath=id('div1')" "shadow" "css=#div2" "shadow" "css=#div3" "shadow"
    
    
    ''',

    # use -js

    'show_progress': 1,

    'opt': {
        # 'humanlike': 1, # slow down a bit, more human-like
        # "browserArgs": ["--disable-notifications"],
    },
}


def code(all_cfg, known, **opt):
    global driver

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

    if opt.get('rm', False):
        # remove the output directory before start
        shutil.rmtree(output_dir, ignore_errors=True)
    else:
        os.makedirs(output_dir, exist_ok=True)  # this does "mkdir -p"

    driver = all_cfg["resources"]["selenium"]["driver"]

    steps = [f'url={url}', 'sleep=2']

    locator_chain = known['REMAININGARGS']
    if run_js:
        js_list = tpsup.seleniumtools.locator_chain_to_js_list(
            locator_chain, trap=trap)
        locator_chain2 = tpsup.seleniumtools.js_list_to_locator_chain(
            js_list)
        steps.extend(locator_chain2)
    else:
        steps.extend(locator_chain)
    
    if opt.get('dump_element', False):
        steps.append(f'dump_element={output_dir}')
    else:
        steps.append(f'dump_all={output_dir}')
                      
    steps.append(f'comment=dumped to {output_dir}')

    print(f'actions = {pformat(steps)}')
    result = tpsup.seleniumtools.follow(driver, steps, **opt)


def parse_input_sub(input: Union[str, list], all_cfg: dict, **opt):
    return {'REMAININGARGS': input}
