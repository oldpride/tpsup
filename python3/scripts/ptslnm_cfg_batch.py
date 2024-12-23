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
TPP3 = f'{TPSUP}/python3/scripts'
HTTP_BASE = 'http://localhost:8000'
FILE_BASE = f'file:///{TPP3}'
EXAMPLE_BASE = HTTP_BASE

our_cfg = {
    'module': 'tpsup.seleniumtools',

    'position_args': [
        # 'url'
    ],

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
            'choices': ['element', 'iframe', 'page', 'all'],
            'help': 'dump the "element", the innest "iframe" only, "page" (the whole page), or "all". default scope is "element"',
        },
        'allowFile': {
            'switches': ['-af', '--allowFile'],
            'default': False,
            'action': 'store_true',
            'help': "allow file:// url; otherwise, we get 'origin' error in console log when switch iframe. but this is security risk. use for testing only",
        },
    },

    'usage_example': f'''
    - To run a local server, 
        cd "{TPP3}"
        python3 -m http.server 8000
      this allows you to use http url, eg, {HTTP_BASE}/shadow_test2_main.html.
      otherwise, use "-af" to run file url, eg {FILE_BASE}/shadow_test2_main.html.
      to print file-url example
        {{{{prog}}}} fe
        {{{{prog}}}} file_example

    - To see all defineded locators
        {{{{prog}}}} locators

    - To clean up chrome persistence and driver logs
        {{{{prog}}}} any -cq

    - has shadows, no iframes, simple pages to test shadows
    {{{{prog}}}} url="{HTTP_BASE}/shadow_test2_main.html" -dump "{HOME}/dumpdir" -rm # without locators
    {{{{prog}}}} url="{HTTP_BASE}/shadow_test2_main.html" -dump "{HOME}/dumpdir" "xpath=id('shadow_host')" "shadow" -rm # with locators

    - has iframes, no shadows
    {{{{prog}}}} url="{HTTP_BASE}/iframe_test1.html" -dump "{HOME}/dumpdir" -rm

    - has both shadows and iframes: iframe over shadow, shadow over iframe
    {{{{prog}}}} url="{HTTP_BASE}/iframe_over_shadow_test_main.html" -dump "{HOME}/dumpdir" -rm
    {{{{prog}}}} url="{HTTP_BASE}/shadow_over_iframe_test_main.html" -dump "{HOME}/dumpdir" -rm

    - test a static page with nested iframes, same origin vs cross origin (has dice.com iframe)
      many website doesn't allow iframe, eg, google, youtube, but dice.com allows iframe. 
    {{{{prog}}}} url="{HTTP_BASE}/iframe_over_shadow_test_main.html" xpath=//iframe[1] iframe xpath=//iframe[1] iframe xpath=//h1[1] -dump "{HOME}/dumpdir" -rm
    {{{{prog}}}} url="{HTTP_BASE}/iframe_test1.html" xpath=//iframe[1] iframe xpath=//iframe[2] iframe xpath=//div[1] -dump "{HOME}/dumpdir2" -rm
    
    - test using js as steps. 
      variable value can either be persisted in python or in js's window or document (ie, window.documnt) object.
      'jsr' is a special code to return js variable to python.
        {{{{prog}}}} url="{HTTP_BASE}/iframe_over_shadow_test_main.html" "js=document.testvar=777" "js=return document.testvar" "code=print(jsr)"
      
    other js directives: js2element, jsfile, jsfile2element, js2print
        {{{{prog}}}} url=newtab "jsfile2elementprint={TPP3}/ptslnm_js_test_google.js" consolelog click key=Enter sleep=3

    js error should stop locator chain
        {{{{prog}}}} url=blank "jsfile2elementprint={TPP3}/ptslnm_js_test_throw.js" consolelog click key=Enter sleep=3

    - test using js to locate. js is much faster.
        in shadow, we can only use css selector to locate
        but once in iframe, even if an iframe inside an shadow root, we can use xpath again.
    {{{{prog}}}} url="{HTTP_BASE}/iframe_over_shadow_test_main.html" sleep=1 "xpath=/html[1]/body[1]/iframe[1]" "iframe" debug_after=url,consolelog "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow" css=span -dump "{HOME}/dumpdir" -rm
    {{{{prog}}}} url="{HTTP_BASE}/iframe_over_shadow_test_main.html" sleep=1 "xpath=/html[1]/body[1]/iframe[1]" "iframe" debug_after=url,consolelog "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow" css=span -dump "{HOME}/dumpdir2" -rm -js
    diff -r dumpdir dumpdir2 # should be the same
    
    - test dump scope: element, page, all
    {{{{prog}}}} url="{HTTP_BASE}/iframe_over_shadow_test_main.html" "xpath=/html[1]/body[1]/iframe[1]" "iframe" "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow" css=span -dump "{HOME}/dumpdir" -rm
    {{{{prog}}}} url="{HTTP_BASE}/iframe_over_shadow_test_main.html" "xpath=/html[1]/body[1]/iframe[1]" "iframe" "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow" css=span -dump "{HOME}/dumpdir" -rm -scope page
    {{{{prog}}}} url="{HTTP_BASE}/iframe_over_shadow_test_main.html" "xpath=/html[1]/body[1]/iframe[1]" "iframe" "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow" css=span -dump "{HOME}/dumpdir" -rm -scope all
    
    - test go up and down in shadow and iframe
    {{{{prog}}}} url="{HTTP_BASE}/iframe_over_shadow_test_main.html" sleep=1 "xpath=/html[1]/body[1]/iframe[1]" "iframe" debug_after=url,consolelog "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow" css=span top
    
    // vs / in xpath:
        // is short path
        / is full path
    {{{{prog}}}} url="{HTTP_BASE}/iframe_nested_test_main.html" sleep=1 "xpath=//iframe[1]" "iframe" debug_after=url,consolelog "xpath=//iframe[2]" "iframe" "xpath=//iframe[1]" "iframe" "xpath=/html/body/div[1]/p[1]" debug_after=url,consolelog,iframestack
    
    - dump out dynamically generated html too
      note:
        - add sleep time to let the page fully loaded.
               for local test page, this is not needed;
               but for remote page, this is needed. otherwise, you get error: 
               stale element reference: element is not attached to the page document
        - once entered shadow, xpath is not working anymore., use css selector instead.
    {{{{prog}}}} url=newtab "sleep=2" "xpath=/iframe[1]" iframe "xpath=//a[@aria-label='Gmail ']" -dump "{HOME}/dumpdir" -rm

    - test block steps
    {{{{prog}}}} code="i=0" code="print(f'i={{i}}')" while=code="i<3" code="i=i+1" code="print(f'i={{i}}')" sleep=1 end_while

    {{{{prog}}}} url="{HTTP_BASE}/ptslnm_test_block.html" wait=1 code="i=0" while=code="i<4" code="i=i+1" click_xpath=/html/body/button sleep=1 "if=xpath=//*[@id=\\"random\\" and text()=\\"10\\"]" we_return end_if end_while

    
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
    debug = opt.get('debug', 0)
    if known['REMAININGARGS'] and (known['REMAININGARGS'][0] == 'fe' or known['REMAININGARGS'][0] == 'file_example'):
        # replace http with file in all_cfg
        if debug:
            print(f'before usage_example={all_cfg['usage_example']}')
        
        # print(pformat(known))
        # prog = os.path.basename(__file__).replace('_cfg_batch.py', '') # this gave batch.py
        prog = 'ptslnm'
        usage_example = all_cfg['usage_example'].replace(HTTP_BASE, FILE_BASE).replace("{{prog}}", f'{prog} -af')
        print()
        print(usage_example)
        exit(0)

    if known['REMAININGARGS'] and known['REMAININGARGS'][0] == 'locators':
        for line in tpsup.seleniumtools.get_defined_locators():
            print(line)
        exit(0)

    # run tpsup.seleniumtools.pre_batch() to set up driver
    tpsup.seleniumtools.pre_batch(all_cfg, known, **opt)

def code(all_cfg, known, **opt):
    # global driver

    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'from code(), known ={pformat(known)}')
        print(f'from code(), opt = {pformat(opt)}')

    dryrun = opt.get('dryrun', 0)
    # url = opt.get('url')
    dump_dir = opt.get('dump_dir')
    run_js = opt.get('js', 0)
    trap = opt.get('trap', 0)
    debug = opt.get('debug', 0)
    allowFile = opt.get('allowFile', 0)

    # yyyy, mm, dd = datetime.datetime.now().strftime("%Y,%m,%d").split(',')

    if dump_dir:
        if opt.get('rm', False):
            # remove the dump directory before start
            shutil.rmtree(dump_dir, ignore_errors=True)
        else:
            os.makedirs(dump_dir, exist_ok=True)  # this does "mkdir -p"

    steps = [
        # f'url={url}', 
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
        steps.append(f'dump_{scope}={dump_dir}')        
        steps.append(f'comment=dumped {scope} to {dump_dir}')

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

    result = tpsup.seleniumtools.follow(steps, **opt)

def parse_input_sub(input: Union[str, list], all_cfg: dict, **opt):
    return {'REMAININGARGS': input}
