#!/usr/bin/env python
import os
import re
from typing import Union

import tpsup.envtools
import tpsup.csvtools
import tpsup.htmltools
import tpsup.seleniumtools
import tpsup.appiumtools
import tpsup.locatetools
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

    'usage_example': f'''

    - test block steps
    {{{{prog}}}} code="i=0" code="print(f'i={{i}}')" while=code="i<3" code="i=i+1" code="print(f'i={{i}}')" sleep=1 end_while

    {{{{prog}}}} if_not=exp="a=0;1/a" code="print('negate False worked')" end_if_not

    {{{{prog}}}} if=dummy=1 tab=1 end_if -m local

    
    ''',

    'show_progress': 1,

    'extra_args': {
        'module' : {
            'switches': ['-m', '--module'],
            'type': str,
            'default': 'selenium',
            'help': 'module to use: selenium, appium, local',
        },
    },

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
    interactive = opt.get('interactive', 0)
    module = opt.get('module')

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

    locate_func = None
    if module == 'selenium':
        locate_func = tpsup.seleniumtools.locate
    elif module == 'appium':
        locate_func = tpsup.appiumtools.locate
    elif module == 'local':
        locate_func = locate
    else:
        raise Exception(f"unknown module={module}")

    followEnv = tpsup.locatetools.FollowEnv(str_action=locate_func, **opt)
    result = followEnv.follow(steps, **opt)


####################################
# the following is only for "-m local" testing
####################################
break_levels = 0
debuggers = {
    'before': [],
    'after': []
}

def locate(locator: str, **opt):
    global break_levels

    interactive = opt.get('interactive', 0)
    dryrun = opt.get('dryrun', 0)

    helper = opt.get('helper', None)

    ret = {'Success': False}
    
    # log_FileFuncLine("locator = " + locator)
    if m := re.match(r"tab=(.+)", locator):
        count_str, *_ = m.groups()
        count = int(count_str)
        print(f"locate: tab {count} times")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            print(f"locate: {locator}")
            ret['Success'] = True
    elif m := re.match(r"dummy=(.+)", locator):
        count_str, *_ = m.groups()
        count = int(count_str)
        print(f"locate: dummy {count} times")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            print(f"locate: {locator}")
            ret['Success'] = True
    elif m := re.match(r"break()$|break=(\d+)", locator):
        ret['Success'] = True # hard code to True for now

        string_levels, *_ = m.groups()

        # default break levels is 1, ie, break one level of while loop.
        # we can use break=999 to break all levels of while loop.
        if string_levels == "":
            break_levels2 = 1
        else:
            break_levels2 = int(string_levels)

        print(f"locate: break break_levels={break_levels2}")
        if not dryrun:
            # we update global break_levels only when we are not in dryrun.
            break_levels = break_levels2

            ret['break_levels'] = break_levels # this is to tell followEnv to break
    elif m := re.match(r"debug_(before|after)", locator):
        ret['Success'] = True # hard code to True for now

        before_after, *_ = m.groups()

        if not dryrun:
            for step in debuggers[before_after]:
                # we don't care about the return value but we should avoid
                # using locator (step) that has side effect: eg, click, send_keys
                print(f"follow: debug_after={step}")
                locate(step, **opt)
    elif m := re.match(r"debug_(before|after)", locator):
        '''
        "debug_before" vs "debug_before=step1,step2"

        "debug_before", ie, without steps, is to execute all debuggers['before'].
        "debug_before=step1,step2" is to update debuggers['before'], not execute them.
        '''
        ret['Success'] = True # hard code to True for now

        before_after, *_ = m.groups()

        if not dryrun:
            for step in debuggers[before_after]:
                # we don't care about the return value but we should avoid
                # using locator (step) that has side effect: eg, click, send_keys
                print(f"follow: debug_after={step}")
                locate(step, **opt)
    else:
        raise Exception(f"unknown locator={locator}")
    
    return ret

    
def parse_input_sub(input: Union[str, list], all_cfg: dict, **opt):
    caller = all_cfg.get('caller', None)

    return {'REMAININGARGS': input}
