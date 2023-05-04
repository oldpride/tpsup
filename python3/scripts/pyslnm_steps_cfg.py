#!/usr/bin/env python
import datetime
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
    'position_args' : ['host_port', 'url', 'output_dir'],

    'extra_args' : [
        # argparse's args
        {
            'dest' : 'headless',
            'default' : False,
            'action' : 'store_true',
            'help' : 'run in headless mode',
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
    {{{{prog}}}} auto "file:///{os.environ['TPSUP']}/python3/scripts/iframe_test1.html" %USERPROFILE%/dumpdir2 xpath=//iframe[1] iframe xpath=//iframe[1] iframe xpath=//h1[1]  -js
    {{{{prog}}}} auto "file:///{os.environ['TPSUP']}/python3/scripts/iframe_test1.html" %USERPROFILE%/dumpdir2 xpath=//iframe[1] iframe xpath=//iframe[1] iframe xpath=//h1[1]
    
    - test a static page with nested iframes, cross origin
    {{{{prog}}}} auto "file:///{os.environ['TPSUP']}/python3/scripts/iframe_test1.html" %USERPROFILE%/dumpdir2 xpath=//iframe[1] iframe xpath=//iframe[2] iframe xpath=//div[1]  -js
    {{{{prog}}}} auto "file:///{os.environ['TPSUP']}/python3/scripts/iframe_test1.html" %USERPROFILE%/dumpdir2 xpath=//iframe[1] iframe xpath=//iframe[2] iframe xpath=//div[1]
    
    - this will dump out dynamically generated html too
    
    {{{{prog}}}} auto chrome-search://local-ntp/local-ntp.html %USERPROFILE%/dumpdir2 xpath=/html/body/ntp-app shadow css=ntp-realbox shadow css=input 
    
    # iframe001: id("backgroundImage")
    # shadow001: /html[@class="focus-outline-visible"]/body[1]/ntp-app[1]
    # shadow001.shadow002: /div[@id="content"]/ntp-iframe[@id="oneGoogleBar"]
    # shadow001.shadow002.iframe002: /iframe[@id="iframe"]
    # div.gb_Id     # <div class="gb_Id">Google apps</div>

    # in shadow, we can only use css selector to locate
    # but once in iframe, even if an iframe inside an shadow root, we can use xpath again.
    
    # from cmd.exe, 
    #   double quotes cannot be escaped, 
    #   single quote is just a letter, cannot do grkouping. 
    # therefore, xpath=//div[@class="gb_Id"] will not work on cmd.exe
    {{{{prog}}}} auto chrome-search://local-ntp/local-ntp.html %USERPROFILE%/dumpdir2 xpath=/html/body/ntp-app shadow css=ntp-iframe shadow "css=#iframe" iframe xpath=//div[3]
    
    # from bash
    {{{{prog}}}} auto chrome-search://local-ntp/local-ntp.html ~/dumpdir2 xpath=/html/body/ntp-app shadow css=ntp-iframe shadow "css=#iframe" iframe 'xpath=//div[@class="gb_Id"]'
    
    # use -js
    {{{{prog}}}} auto chrome-search://local-ntp/local-ntp.html %USERPROFILE%/dumpdir2 xpath=/html/body/ntp-app shadow css=ntp-iframe shadow "css=#iframe" iframe xpath=//div[3] -js
    
    {{{{prog}}}} auto chrome-untrusted://new-tab-page/one-google-bar?paramsencoded= %USERPROFILE%/dumpdir2 xpath=//div[3] -js
    
    # test a cross domain iframe
    {{{{prog}}}} auto https://www.dice.com %USERPROFILE%/dumpdir2 xpath=//iframe[4] iframe xpath=//script[1]
    {{{{prog}}}} auto https://www.dice.com %USERPROFILE%/dumpdir2 xpath=//iframe[4] iframe xpath=//script[1] -js
    
    # dump whole page, print xpath shortcut, eg id("mycontainer")
    {{{{prog}}}} auto chrome-search://local-ntp/local-ntp.html %USERPROFILE%/dumpdir2 xpath=/html
    
    # dump whole page, print full xpath
    {{{{prog}}}} auto chrome-search://local-ntp/local-ntp.html %USERPROFILE%/dumpdir2 xpath=/html -full
    ''',

    # use -js

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
    output_dir = opt.get('output_dir')
    run_js = opt.get('js', 0)
    trap = opt.get('trap', 0)

    yyyy, mm, dd = datetime.datetime.now().strftime("%Y,%m,%d").split(',')
    os.makedirs(output_dir, exist_ok=True) # this does "mkdir -p"

    if driver is None:
        method = all_cfg["resources"]["selenium"]["driver_call"]['method']
        kwargs = all_cfg["resources"]["selenium"]["driver_call"]["kwargs"]
        driver = method(**{**kwargs, "dryrun":0}) # overwrite kwargs

    actions = [
        [f'url={url}', 'sleep=2', 'go to url'],
    ]

    locator_chain = known['REMAININGARGS']
    if run_js:
        js_list = tpsup.seleniumtools.locator_chain_to_js_list(locator_chain, trap=trap)
        locator_chain2 = tpsup.seleniumtools.js_list_to_locator_chain(js_list)
        actions.append([locator_chain2, f'dump_element={output_dir}', f'dump element to {output_dir}'])
    else:
        actions.append([locator_chain, f'dump_element={output_dir}', f'dump element to {output_dir}'])

    print(f'actions = {pformat(actions)}')
    result = tpsup.seleniumtools.follow(driver, actions, **opt)

def parse_input_sub(input: Union[str, list], all_cfg: dict, **opt):
    return { 'REMAININGARGS' : input }

def post_batch(all_cfg, known, **opt):
    global driver
    print(f'running post batch')
    driver.quit()
    if tpsup.pstools.prog_running('chromed', printOutput=1):
        print(f"seeing leftover chrome")
