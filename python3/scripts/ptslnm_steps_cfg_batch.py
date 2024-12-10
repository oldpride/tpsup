#!/usr/bin/env python
import datetime
import os
import time
from typing import Union

import tpsup.envtools
import tpsup.csvtools
import tpsup.htmltools
import tpsup.seleniumtools
import tpsup.pstools
from pprint import pformat
from selenium import webdriver


our_cfg = {

    'resources': {
        'selenium': {
            'method': tpsup.seleniumtools.get_driver,
            'cfg': {
                # 'host_port': 'auto'
            },
            # we delay the driver init till we really need it.
            'init_resource': 0,
        },
    },

    # position_args will be inserted into $opt hash to pass forward
    'position_args': ['url'],

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
    },

    'usage_example': f'''
    - test a static page with nested iframes, same origin
    {{{{prog}}}} "file:///{os.environ['TPSUP']}/python3/scripts/iframe_test1.html" xpath=//iframe[1] iframe xpath=//iframe[1] iframe xpath=//h1[1]
    
    - test a static page with nested iframes, cross origin
    {{{{prog}}}} "file:///{os.environ['TPSUP']}/python3/scripts/iframe_test1.html" xpath=//iframe[1] iframe xpath=//iframe[2] iframe xpath=//div[1]
    
    - block example
    {{{{prog}}}} "about:blank" code="i=0" code="print(f'i={{i}}')" while=code="i<3" code="i=i+1" code="print(f'i={{i}}')" sleep=1 end_while

    {{{{prog}}}} "file:///{os.environ['TPSUP']}/python3/scripts/ptslnm_steps_test_block.html" click_xpath=/html/body/button sleep=3

    {{{{prog}}}} "file:///{os.environ['TPSUP']}/python3/scripts/ptslnm_steps_test_block.html" wait=1 code="i=0" while=code="i<4" code="i=i+1" click_xpath=/html/body/button sleep=1 "if=xpath=//*[@id=\\"random\\" and text()=\\"10\\"]" we_return end_if end_while

    #//*[@id="random" and not(text() = "5"]

    - this will dump out dynamically generated html too
    
    {{{{prog}}}} chrome-search://local-ntp/local-ntp.html xpath=/html/body/ntp-app shadow css=ntp-realbox shadow css=input 
    
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
    {{{{prog}}}} chrome-search://local-ntp/local-ntp.html xpath=/html/body/ntp-app shadow css=ntp-iframe shadow "css=#iframe" iframe xpath=//div[3]
    
    # from bash
    {{{{prog}}}} chrome-search://local-ntp/local-ntp.html xpath=/html/body/ntp-app shadow css=ntp-iframe shadow "css=#iframe" iframe 'xpath=//div[@class="gb_Id"]'
    
    # use -js
    {{{{prog}}}} chrome-search://local-ntp/local-ntp.html xpath=/html/body/ntp-app shadow css=ntp-iframe shadow "css=#iframe" iframe xpath=//div[3] -js
    
    {{{{prog}}}} chrome-untrusted://new-tab-page/one-google-bar?paramsencoded= xpath=//div[3] -js
    
    # test a cross domain iframe
    {{{{prog}}}} https://www.dice.com xpath=//iframe[4] iframe xpath=//script[1]
    {{{{prog}}}} https://www.dice.com xpath=//iframe[4] iframe xpath=//script[1] -js
    
    # dump whole page, print xpath shortcut, eg id("mycontainer")
    {{{{prog}}}} chrome-search://local-ntp/local-ntp.html xpath=/html
    
    # dump whole page, print full xpath
    {{{{prog}}}} chrome-search://local-ntp/local-ntp.html xpath=/html -full
    ''',

    # use -js

    'show_progress': 1,

    'opt': {
        # 'humanlike': 1, # slow down a bit, more human-like
        # "browserArgs": ["--disable-notifications"],
    },
}

# we define this globally so that post_code() can use it too
driver: webdriver.Chrome = None


def code(all_cfg, known, **opt):
    global driver

    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'from code(), known ={pformat(known)}')
        print(f'from code(), opt = {pformat(opt)}')

    dryrun = opt.get('dryrun', 0)
    url = opt.get('url')
    run_js = opt.get('js', 0)
    trap = opt.get('trap', 0)

    if driver is None:
        method = all_cfg["resources"]["selenium"]["driver_call"]['method']
        kwargs = all_cfg["resources"]["selenium"]["driver_call"]["kwargs"]
        driver = method(**{**kwargs, "dryrun": 0})  # overwrite kwargs

    steps = [f'url={url}', 'sleep=2']

    steps.extend(known['REMAININGARGS'])        

    print(f'steps = {pformat(steps)}')
    result = tpsup.seleniumtools.follow(driver, steps, **opt)


def parse_input_sub(input: Union[str, list], all_cfg: dict, **opt):
    return {'REMAININGARGS': input}


def post_batch(all_cfg, known, **opt):
    global driver
    print(f'running post batch')
    driver.quit()
    if tpsup.pstools.ps_grep('chromed', printOutput=1):
        print(f"seeing leftover chrome")
