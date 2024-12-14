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

    'position_args': ['url'],

    'extra_args': {
        'js': {'switches': ['-js', '--js'],
               'default': False,
               'action': 'store_true',
               'help': 'run locator in js. js only accept locators: xpath, css, shadow, or iframe'
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
            # remove the dump directory before start
            'switches': ['-rm', '--rm'],
            'default': False,
            'action': 'store_true',
            'help': 'remove the dump directory before start',
        },
        'dump_dir': {
            # dump directory
            'switches': ['-dump', '--dump'],
            'default': None,
            'action': 'store',
            'help': 'dump details to this directory. default is not to dump',
        },
        'scope': {
            # dump scope
            'switches': ['-scope', '--scope'],
            'default': 'element',
            'choices': ['element', 'dom', 'all'],
            'help': 'dump the "element", the innest "dom" (iframe or shadow) only, or "all" (the whole page). default scope is "element"',
        }
    },

    'usage_example': f'''
    - has shadows, no iframes, simple pages to test shadows
    {{{{prog}}}} -rm "file:///{TPSUP}/python3/scripts/shadow_test2_main.html" -dump "{HOME}/dumpdir" # without locators
    {{{{prog}}}} -rm "file:///{TPSUP}/python3/scripts/shadow_test2_main.html" -dump "{HOME}/dumpdir" "xpath=id('shadow_host')" "shadow"

    - has iframes, no shadows
    {{{{prog}}}} -rm "file:///{TPSUP}/python3/scripts/iframe_test1.html" -dump "{HOME}/dumpdir"

    - has both shadows and iframes: iframe over shadow, shadow over iframe
    {{{{prog}}}} -rm "file:///{TPSUP}/python3/scripts/iframe_over_shadow_test_main.html" -dump  "{HOME}/dumpdir"
    {{{{prog}}}} -rm "file:///{TPSUP}/python3/scripts/shadow_over_iframe_test_main.html" -dump  "{HOME}/dumpdir"

    - test a static page with nested iframes, same origin vs cross origin (has dice.com iframe)
      many website doesn't allow iframe, eg, google, youtube, but dice.com allows iframe. 
    {{{{prog}}}} "file:///{TPSUP}/python3/scripts/iframe_over_shadow_test_main.html" -dump  "{HOME}/dumpdir" xpath=//iframe[1] iframe xpath=//iframe[1] iframe xpath=//h1[1]
    {{{{prog}}}} "file:///{TPSUP}/python3/scripts/iframe_test1.html" -dump "{HOME}/dumpdir2" xpath=//iframe[1] iframe xpath=//iframe[2] iframe xpath=//div[1]
    
    - test js. js is much faster.
        in shadow, we can only use css selector to locate
        but once in iframe, even if an iframe inside an shadow root, we can use xpath again.
    {{{{prog}}}} -rm "file:///{TPSUP}/python3/scripts/iframe_over_shadow_test_main.html" -dump "{HOME}/dumpdir" sleep=1 "xpath=/html[1]/body[1]/iframe[1]" "iframe" "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow" css=span
    {{{{prog}}}} -rm "file:///{TPSUP}/python3/scripts/iframe_over_shadow_test_main.html" -dump "{HOME}/dumpdir" sleep=1 "xpath=/html[1]/body[1]/iframe[1]" "iframe" "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow" css=span -js
    diff -r dumpdir dumpdir2 # should be the same
    
    - test dump scope: element, dom, all
    {{{{prog}}}} -rm "file:///{TPSUP}/python3/scripts/iframe_over_shadow_test_main.html" -dump  "{HOME}/dumpdir" "xpath=/html[1]/body[1]/iframe[1]" "iframe" "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow" css=span
    {{{{prog}}}} -rm "file:///{TPSUP}/python3/scripts/iframe_over_shadow_test_main.html" -dump "{HOME}/dumpdir" "xpath=/html[1]/body[1]/iframe[1]" "iframe" "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow" css=span -scope dom
    {{{{prog}}}} -rm "file:///{TPSUP}/python3/scripts/iframe_over_shadow_test_main.html" -dump  "{HOME}/dumpdir" "xpath=/html[1]/body[1]/iframe[1]" "iframe" "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow" css=span -scope all
    
    - dump out dynamically generated html too
      note:
        - add sleep time to let the page fully loaded.
               for local test page, this is not needed;
               but for remote page, this is needed. otherwise, you get error: 
               stale element reference: element is not attached to the page document
        - once entered shadow, xpath is not working anymore., use css selector instead.
    {{{{prog}}}} chrome://new-tab-page -dump "{HOME}/dumpdir" "sleep=2" "xpath=/iframe[1]" iframe "xpath=//a[@aria-label='Gmail ']"

    - test block steps
    {{{{prog}}}} "about:blank" code="i=0" code="print(f'i={{i}}')" while=code="i<3" code="i=i+1" code="print(f'i={{i}}')" sleep=1 end_while

    {{{{prog}}}} "file:///{os.environ['TPSUP']}/python3/scripts/ptslnm_steps_test_block.html" wait=1 code="i=0" while=code="i<4" code="i=i+1" click_xpath=/html/body/button sleep=1 "if=xpath=//*[@id=\\"random\\" and text()=\\"10\\"]" we_return end_if end_while

    
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
    global driver

    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'from code(), known ={pformat(known)}')
        print(f'from code(), opt = {pformat(opt)}')

    dryrun = opt.get('dryrun', 0)
    url = opt.get('url')
    dump_dir = opt.get('dump_dir')
    run_js = opt.get('js', 0)
    trap = opt.get('trap', 0)
    debug = opt.get('debug', 0)

    # yyyy, mm, dd = datetime.datetime.now().strftime("%Y,%m,%d").split(',')

    if dump_dir:
        if opt.get('rm', False):
            # remove the dump directory before start
            shutil.rmtree(dump_dir, ignore_errors=True)
        else:
            os.makedirs(dump_dir, exist_ok=True)  # this does "mkdir -p"

    driver = all_cfg["resources"]["selenium"]["driver"]

    steps = [
        f'url={url}', 
        # 'sleep=2'
    ]

    locator_chain = known['REMAININGARGS']
    if run_js:
        locator_chain2 = tpsup.seleniumtools.locator_chain_to_locator_chain_using_js(locator_chain, trap=trap, debug=debug)
        steps.extend(locator_chain2)
    else:
        steps.extend(locator_chain)
    
    if dump_dir:
        scope = opt.get('scope', 'element')
        if scope == 'dom':
            steps.append(f'dump_dom={dump_dir}')
        elif scope == 'all':
            steps.append(f'dump_all={dump_dir}')
        else:
            steps.append(f'dump_element={dump_dir}')
                        
        steps.append(f'comment=dumped to {dump_dir}')

    print(f'steps = {pformat(steps)}')
    result = tpsup.seleniumtools.follow(driver, steps, **opt)


def parse_input_sub(input: Union[str, list], all_cfg: dict, **opt):
    return {'REMAININGARGS': input}
