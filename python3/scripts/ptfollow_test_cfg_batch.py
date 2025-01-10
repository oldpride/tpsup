#!/usr/bin/env python
import os
import re
from typing import Union

import tpsup.envtools
import tpsup.csvtools
import tpsup.htmltools
import tpsup.seleniumtools
import tpsup.followtools
from tpsup.logbasic import log_FileFuncLine
import tpsup.pstools
from pprint import pformat

from tpsup.utilbasic import hit_enter_to_continue

HOME = tpsup.envtools.get_home_dir()
TPSUP = os.environ['TPSUP']
TPP3 = f'{TPSUP}/python3/scripts'
HTTP_BASE = 'http://localhost:8000'
FILE_BASE = f'file:///{TPP3}'
EXAMPLE_BASE = HTTP_BASE

our_cfg = {
    # 'module': 'tpsup.seleniumtools',

    # 'position_args': [
    #     # 'url'
    # ],

    # 'extra_args': {
    # },

    'test_example': f'''
    the expected results are created wehn using http url to test.
    ptslnm url="{HTTP_BASE}//iframe_over_shadow_test_main.html" "xpath=/html[1]/body[1]/iframe[1]" "iframe" "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow" "css=iframe" iframe css=p dump_all="{HOME}/dumpdir"
    diff -r ~/dumpdir {TPP3}/expected/ptslnm_test1/dumpdir
    ''',

    'usage_example': f'''
    - To run a local server, 
        cd "{TPP3}"
        python3 -m http.server 8000
      this allows you to use http url, eg, {HTTP_BASE}/shadow_test2_main.html.
      otherwise, use "-af" to run file url, eg {FILE_BASE}/shadow_test2_main.html.
      to print file-url example
            {{{{prog}}}} fe
            {{{{prog}}}} file_example
        to print test example
            {{{{prog}}}} test
            {{{{prog}}}} test_example
        to print test example with file url   
            {{{{prog}}}} ft
            {{{{prog}}}} file_test
        to download chromedriver
            {{{{prog}}}} ddriver [130.0]
            {{{{prog}}}} download_chromedriver [130.0]
        to check setup
            {{{{prog}}}} check_setup

    - To see all defineded locators
        {{{{prog}}}} locators

    - To clean up chrome persistence and driver logs
        {{{{prog}}}} any -cq

    - has shadows, no iframes, simple pages to test shadows, default dump scope is element, default dump dir is $HOME/dumpdir
    {{{{prog}}}} url="{HTTP_BASE}/shadow_test2_main.html" dump_page="{HOME}/dumpdir" # without locators, dump whole page
    {{{{prog}}}} url="{HTTP_BASE}/shadow_test2_main.html" "xpath=id('shadow_host')" "shadow" dump # with locators

    - has iframes, no shadows
    {{{{prog}}}} url="{HTTP_BASE}/iframe_test1.html" dump

    - has both shadows and iframes: iframe over shadow, shadow over iframe
    {{{{prog}}}} url="{HTTP_BASE}/iframe_over_shadow_test_main.html" dump
    {{{{prog}}}} url="{HTTP_BASE}/shadow_over_iframe_test_main.html" dump

    - test a static page with nested iframes, same origin vs cross origin (has dice.com iframe)
      many website doesn't allow iframe, eg, google, youtube, but dice.com allows iframe. 
    {{{{prog}}}} url="{HTTP_BASE}/iframe_over_shadow_test_main.html" xpath=//iframe[1] iframe xpath=//iframe[1] iframe xpath=//h1[1] dump
    {{{{prog}}}} url="{HTTP_BASE}/iframe_test1.html" xpath=//iframe[1] iframe xpath=//iframe[2] iframe xpath=//div[1] dump
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
    {{{{prog}}}} url="{HTTP_BASE}/iframe_over_shadow_test_main.html" sleep=1 "xpath=/html[1]/body[1]/iframe[1]" "iframe" debug_after=url,consolelog "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow" css=span dump="{HOME}/dumpdir"
    {{{{prog}}}} url="{HTTP_BASE}/iframe_over_shadow_test_main.html" sleep=1 "xpath=/html[1]/body[1]/iframe[1]" "iframe" debug_after=url,consolelog "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow" css=span dump="{HOME}/dumpdir2" -js
    diff -r dumpdir dumpdir2 # should be the same
    
    - test dump scope: element, shadow, iframe, page, all
    {{{{prog}}}} url="{HTTP_BASE}/iframe_over_shadow_test_main.html" "xpath=/html[1]/body[1]/iframe[1]" "iframe" "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow" css=iframe iframe css=p dump
    {{{{prog}}}} url="{HTTP_BASE}/iframe_over_shadow_test_main.html" "xpath=/html[1]/body[1]/iframe[1]" "iframe" "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow" css=iframe iframe css=p dump_all 

    - test go up and down in shadow and iframe
    {{{{prog}}}} url="{HTTP_BASE}/iframe_over_shadow_test_main.html" sleep=1 "xpath=/html[1]/body[1]/iframe[1]" "iframe" debug_after=url,consolelog "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow" css=span top
    
    // vs / in xpath:
        // is short path
        / is full path
    {{{{prog}}}} url="{HTTP_BASE}/iframe_nested_test_main.html" sleep=1 debug_after=url,consolelog,domstack "xpath=//iframe[1]" "iframe" "xpath=//iframe[2]" "iframe" "xpath=//iframe[1]" "iframe" "xpath=/html/body/div[1]/p[1]"
    
    - dump out dynamically generated html too
      note:
        - add sleep time to let the page fully loaded.
               for local test page, this is not needed;
               but for remote page, this is needed. otherwise, you get error: 
               stale element reference: element is not attached to the page document
        - once entered shadow, xpath is not working anymore., use css selector instead.
    {{{{prog}}}} url=newtab "sleep=2" "xpath=/iframe[1]" iframe "xpath=//a[@aria-label='Gmail ']" dump="{HOME}/dumpdir"

    - test block steps
    {{{{prog}}}} code="i=0" code="print(f'i={{i}}')" while=code="i<3" code="i=i+1" code="print(f'i={{i}}')" sleep=1 end_while

    {{{{prog}}}} if_not=exp="a=0;1/a" code="print('negate False worked')" end_if_not

    {{{{prog}}}} url="{HTTP_BASE}/ptslnm_test_block.html" wait=1 code="i=0" while=code="i<4" code="i=i+1" click_xpath=/html/body/button sleep=1 "if=xpath=//*[@id=\\"random\\" and text()=\\"10\\"]" break end_if end_while

    - test exp
    {{{{prog}}}} exp="a=1;a+1" code="print(a)"  # this will pass - 2
    {{{{prog}}}} exp="a=1"     code="print(a)"  # this will fail - NameError: name 'a' is not defined
    {{{{prog}}}} code="a=1"    code="print(a)"  # this will pass - 1

    - test steps in file
    {{{{prog}}}} url="{HTTP_BASE}/iframe_over_shadow_test_main.html" steps_txt="{TPP3}/ptslnm_test_steps_txt.txt" top
    {{{{prog}}}} url="{HTTP_BASE}/iframe_over_shadow_test_main.html"  steps_py="{TPP3}/ptslnm_test_steps_py.py"   top

    - test parallel steps - string
    {{{{prog}}}} url="{HTTP_BASE}/iframe_nested_test_main.html" sleep=1 "xpath=//iframe[1],css=p" print=html
    {{{{prog}}}} url="{HTTP_BASE}/iframe_nested_test_main.html" sleep=1 "css=p,xpath=//iframe[1]" print=html

    - test dict step - besides provide parallellism, it also provides a mini if-else logic 
    {{{{prog}}}} url="{HTTP_BASE}/iframe_nested_test_main.html" sleep=1 "dictfile={TPP3}/ptslnm_test_dict_simple.py" debug=domstack,iframestack
    
    - test parallel steps - dict - parallel type
    {{{{prog}}}} url="{HTTP_BASE}/iframe_nested_test_main.html" sleep=1 "dictfile={TPP3}/ptslnm_test_dict_parallel.py" debug=domstack,iframestack
    
    - test parallel steps - dict - chains type
    {{{{prog}}}} url="{HTTP_BASE}/iframe_over_shadow_test_main.html" sleep=1 "dictfile={TPP3}/ptslnm_test_dict_chains.py" debug=domstack,iframestack print=tag
    
    - test alert popup - alert popup doesn't show up as o 2024/12/30
    {{{{prog}}}} url="{HTTP_BASE}/ptslnm_test_alert.html" "xpath=//input[@id='fname']" click string=henry tab=1 url_accept_alert=http://google.com sleep=1
    
    - test clear text field
    {{{{prog}}}} url="{HTTP_BASE}/ptslnm_test_input.html" "xpath=//textarea[id('message')]" click clear_text code2element='f"abc{{1+1}}"' sleep=10

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

# def pre_batch(all_cfg, known, **opt):
#     # run tpsup.seleniumtools.pre_batch() to set up driver
#     tpsup.seleniumtools.pre_batch(all_cfg, known, **opt)

def code(all_cfg, known, **opt):
    # global driver

    debug = opt.get('debug', 0)
    if debug:
        print(f'from code(), known ={pformat(known)}')
        print(f'from code(), opt = {pformat(opt)}')

    dryrun = opt.get('dryrun', 0)
    run_js = opt.get('js', 0)
    trap = opt.get('trap', 0)
    debug = opt.get('debug', 0)
    allowFile = opt.get('allowFile', 0)

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

    followEnv = tpsup.followtools.FollowEnv(str_action=tpsup.seleniumtools.locate, **opt)
    result = followEnv.follow(steps, **opt)

break_levels = 0
debuggers = {
    'before': [],
    'after': []
}

# def locate(locator: str, **opt):
#     global break_levels

#     interactive = opt.get('interactive', 0)
#     dryrun = opt.get('dryrun', 0)

#     helper = opt.get('helper', None)

#     ret = {'Success': False}
    
#     # log_FileFuncLine("locator = " + locator)
#     if m := re.match(r"tab=(.+)", locator):
#         count_str, *_ = m.groups()
#         count = int(count_str)
#         print(f"locate: tab {count} times")
#         if interactive:
#             hit_enter_to_continue(helper=helper)
#         if not dryrun:
#             print(f"locate: {locator}")
#             ret['Success'] = True
#     elif m := re.match(r"dummy=(.+)", locator):
#         count_str, *_ = m.groups()
#         count = int(count_str)
#         print(f"locate: dummy {count} times")
#         if interactive:
#             hit_enter_to_continue(helper=helper)
#         if not dryrun:
#             print(f"locate: {locator}")
#             ret['Success'] = True
#     elif m := re.match(r"break()$|break=(\d+)", locator):
#         ret['Success'] = True # hard code to True for now

#         string_levels, *_ = m.groups()

#         # default break levels is 1, ie, break one level of while loop.
#         # we can use break=999 to break all levels of while loop.
#         if string_levels == "":
#             break_levels2 = 1
#         else:
#             break_levels2 = int(string_levels)

#         print(f"locate: break break_levels={break_levels2}")
#         if not dryrun:
#             # we update global break_levels only when we are not in dryrun.
#             break_levels = break_levels2

#             ret['break_levels'] = break_levels # this is to tell followEnv to break
#     elif m := re.match(r"debug_(before|after)", locator):
#         ret['Success'] = True # hard code to True for now

#         before_after, *_ = m.groups()

#         if not dryrun:
#             for step in debuggers[before_after]:
#                 # we don't care about the return value but we should avoid
#                 # using locator (step) that has side effect: eg, click, send_keys
#                 print(f"follow: debug_after={step}")
#                 locate(step, **opt)
#     else:
#         raise Exception(f"unknown locator={locator}")
    
#     return ret

    
def parse_input_sub(input: Union[str, list], all_cfg: dict, **opt):
    caller = all_cfg.get('caller', None)

    # if user enter 'example', then we print out usage_example and quit
    if re.match(r'example$', input[0]):
        print(all_cfg.get('usage_example', '').replace("{{prog}}", caller))
        exit(0)

    
    if re.match(r'^(test|test_example)$', input[0]):
        print(all_cfg.get('test_example', '').replace("{{prog}}", caller))
        exit(0)


    return {'REMAININGARGS': input}
