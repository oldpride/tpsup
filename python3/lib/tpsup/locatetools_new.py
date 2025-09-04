import inspect
import os
from pprint import pformat
import re
import shlex
import time
from typing import Union
import tpsup.cmdtools
import tpsup.envtools
from tpsup.nettools import is_tcp_open
import tpsup.pstools
import tpsup.utilbasic
import tpsup.interactivetools
from tpsup.logbasic import log_FileFuncLine
import tpsup.steptools

ret0 = {
    'Success': True, 
    'bad_input': False, # bad input
    'break_levels': 0, 
    'continue_levels': 0
}

class LocateEnv:
    def __init__(self,
                locate_f: callable,

                # for explore()
                locate_usage: dict = None,    
                display_f: callable = None,   

                 **opt):

        if not callable(locate_f):
            raise RuntimeError(f"locate_f is not callable")

        self.locate_f = locate_f
        self.display_f = display_f
        
        # hope we will never need this
        # self.caller_globals = inspect.currentframe().f_back.f_globals
        # self.caller_locals = inspect.currentframe().f_back.f_locals

        self.already_checked_syntax = False
        self.delay = 0 # delay between steps

        self.usage_by_long = {
            'help': {
                'short': 'h',
                'usage': '''
                    show this help message
                    example:
                        help
                        h
                        h steps_py
                ''',
            },
            'quit': {
                'short': 'q',
                'usage': '''
                    quit the program
                    example:
                        quit
                        q
                ''',
            },
            'steps': {
                'no_arg': True,
                'usage': '''
                    enter steps to follow, end with END
                    example:
                        file=c:/users/me/steps.txt # this load a file that contains steps
                        type=pwd{END}
                        END

                ''',
            },
            'steps_txt': {
                'siblings': ['steps_py', 'script'], # siblings are commands that share the same usage.
                'need_arg': True,
                'usage': '''
                    file that contains steps
                        steps_txt=file.txt
                            this is a text file that contains steps, just like command line.
                            steps can be in multiple lines.
                            multiple steps can be in a single line. (we use shell-like syntax)
                            there can be blank and comment lines (starting with #).
                        steps_py=file.py
                            this is a python file that contains steps, but is a python list of steps.
                        
                        'script' is an alias of steps_txt
                    ''',
            },
        }

        # locate_usage is for explore()
        if locate_usage:
            self.usage_by_long.update(locate_usage)

        reserved_keys = ['break', 'continue' ]

        locate_usage_keys = list(self.usage_by_long.keys())
        # get the keys out to avoid dict size change during iteration
        # RuntimeError: dictionary changed size during iteration

        for k in locate_usage_keys:
            if k in reserved_keys:
                raise RuntimeError(f"locator {k} in usage is a reserved keyword")
            
            lu = self.usage_by_long[k]

            # add 'siblings' to each locator usage
            siblings = lu.get('siblings', [])
            for sibling in siblings:
                if sibling in reserved_keys:
                    raise RuntimeError(f"locator {k}'s sibling {sibling} is a reserved keyword")
                if sibling in self.usage_by_long:
                    raise RuntimeError(f"locator {k}'s sibling {sibling} is seen multiple times")
                self.usage_by_long[sibling] = lu.copy()

        self.usage_by_long_and_short = self.usage_by_long.copy()    
        long_keys = list(self.usage_by_long.keys())
        for k in long_keys:
            lu = self.usage_by_long[k]
            short = lu.get('short', None)
            if short:
                if short in reserved_keys:
                    raise RuntimeError(f"locator {k} short {short} is a reserved keyword")
                if short in self.usage_by_long_and_short:
                    raise RuntimeError(f"locator {k} short {short} is seen multiple times")
                self.usage_by_long_and_short[short] = lu.copy()
                self.usage_by_long_and_short[short]['short_for'] = k

    def follow2(self, steps: list,  **opt) -> dict:
        '''
        follow2() follows steps in sequence; its basic flow is: if ... then if ... then if ... then ...

        for example: [ 'click_xpath=/a/b', '"iframe', 'click_xpath=/c/d', 'string="hello world"', 'dump' ]
        By default, if any 'if' failed, we stop. For example, if 'click_xpath=/a/b' failed, we stop.
        If any 'then if' failed, we stop. For example, if 'iframe' failed, we stop.

        as of now, we only allow follow2() to be recursive on block-statement (if/while) level; once
        follow2() calls locate() (eg, in seleniumtools.py), locate() will not call follow2(). 
        This is to avoid infinite recursion.

        With separation of follow2() and locate(), we can implement them in separate modules,
            follow2() is in locatetools.py, 
            locate() is in seleniumtools.py.

            follow2() can recursively call follow2() because the recursion stays in locatetools.py.
            locate() can recursively call locate() because the recursion stays in seleniumtools.py.

            follow2() can call locate() but locate() should not call follow2(). this is to avoid 
            infinite recursion.

        follow2() recursion happens when it handles if/while block.
        '''

        debug = opt.get("debug", 0)
        dryrun = opt.get("dryrun", 0)
        interactive = opt.get("interactive", 0)

        block = [] # this is the current block, which may contain nested block

        '''
        we use block_stack to keep track of nested block. each element is like 
            {
                'blockstart': 'if',
                'condition': 'exp=a==1',
                'negation': False,
                'blockend': 'end_if',
            }
        '''
        block_stack = []

        # ret = {'Success': False, 'break_levels': 0, 'continue_levels': 0}
        ret = ret0.copy()
        ret['Success'] = False

        if not steps:
            raise RuntimeError(f"steps is empty")

        for step in steps:
            if debug:
                print(f"follow2: step={pformat(step)}")

            step_type = type(step)

            # first handle control block. block start and block end are strings only.
            if step_type == str:
                if block_stack:
                    # we are in a block
                    block_info=block_stack[-1]

                    blockstart = block_info['blockstart']
                    condition = block_info['condition']
                    negation = block_info['negation']
                    blockend = block_info['blockend']

                    if step == blockend:
                        # step matches the expected blockend
                        block_stack.pop()

                        if not block_stack:
                            # the outermost of a recursive block is ended; we will run the block now.
                            if debug:
                                print(f"follow2: matched expected_blockend={blockend}")

                            print(f"follow2: seeing blockend={blockend}, run: condition={condition}, negation={negation}, block={block}")

                            if not block:
                                raise RuntimeError(f"block is empty")
                        
                            # run_block() recursively calls follow2()
                            result = self.run_block(blockstart, negation, condition, block, **opt)   

                            if debug:
                                print(f"follow2: run_block result={pformat(result)}")

                            # reset block, negation. blockend_stack is already empty.
                            block = [] 

                            if dryrun:
                                # we only check syntax, therefore, we don't check the result and move on
                                continue

                            # always check break_levels first, before check 'Success'. Because if break_levels > 0,
                            # we should break the loop, no matter 'Success' is True or False.
                            if result['break_levels']:
                                print(f"follow2: break because block result break_levels={result['break_levels']} > 0")
                                # break_levels will be consumed by while-loop in run_block().
                                ret['break_levels'] = result['break_levels']
                                break

                            if result['continue_levels']:
                                print(f"follow2: break because block result continue_levels={result['continue_levels']} > 0")
                                # 'continue_levels' will be consumed by while-loop in run_block().
                                ret['continue_levels'] = result['continue_levels']
                                break

                            if not result['executed']:
                                # the block's condition is not met, we skip the block. we don't break.
                                print(f"follow2: block failed at condition and was skipped. we carry on")
                            elif not result['Success']:
                                print(f"follow2: break because block failed.")
                                # if the block failed, we stop
                                break
                        else:
                            # block_stack is not empty, we are still in a nested block
                            if debug:
                                print(f"follow2: matched a nested blockend={blockend}")

                            # we keep the nested block end in the block, so that we can recursively call run_block()
                            block.append(step)
                    elif m := re.match(r"\s*(end_while|end_if)$", step, flags=re.IGNORECASE):
                        # this is an unexpected blockend
                        raise RuntimeError(f"unexpected blockend={step}")
                    elif m := re.match(r"\s*(while|if)(_not)?=(.+)", step, flags=re.IGNORECASE):
                        # this is a nested block
                        blockstart, negation, condition = m.groups()
                        blockend = f"end_{blockstart}"
                        block_stack.append({
                            'blockstart': blockstart,
                            'negation': negation,
                            'condition': condition,
                            'blockend': blockend,
                        })
                        if debug:
                            print(f"follow2: blockstart={blockstart}, negation={negation}, condition={condition}, "
                                f"expected_blockend={blockend}, block_stack={block_stack}")
                        block.append(step)
                    else:
                        # this is neither blockend nor blockstart. while we are in a block, we save the step to the block.
                        # nested block 
                        block.append(step)

                    continue

                # now that we are not in any block, block list should be empty.
                if block:
                    # we should never be here, because we should have handled all block cases above.
                    # we keep this for debugging purpose.
                    raise RuntimeError(f"unexpected block={block} when block_stack={block_stack}")
                
                # now that we are not in any block, there should be no 'else'
                if step == 'else':
                    raise RuntimeError(f"unexpected 'else' outside of any block")
                
                if m := re.match(r"(end_if|end_while)$", step):
                    raise RuntimeError(f"unexpected blockend={step} when outside of any block, block_stack={block_stack}")

                if result := handle_break(step, **opt):
                    if dryrun:
                        # dryrun is to check syntax only, we don't check the result and move on
                        continue

                    # not dryrun, we check the result
                    # we found the expected break
                    ret['break_levels'] = result['break_levels']
                    ret['continue_levels'] = result['continue_levels']
                    # when matched any break statement, we break, no matter 'Success' is True or False.
                    break

                # if result := handle_common_steps(step, **opt):
                #     continue

                # now that we are not in any block, we check whether this step is a start of a block (not a nested block)
                if m := re.match(r"\s*(while|if)(_not)?=(.+)", step):
                    # we are starting a new block
                    blockstart = m.group(1)
                    negation = m.group(2)
                    condition = m.group(3)

                    '''
                    if/if_not=condition  ... end_if
                    while/while_not=condition ... end_while
                    '''
                    blockend = f"end_{blockstart}"

                    block_stack.append({
                        'blockstart': blockstart,
                        'negation': negation,
                        'condition': condition,
                        'blockend': blockend,
                    })

                    block = []
                    if debug:
                        print(f"follow2: blockstart={blockstart}, negation={negation}, condition={condition}, "
                            f"expected_blockend={blockend}, block_stack={block_stack}")
                    continue

                if m := re.match(r"\s*steps_(txt|py)=(.+)", step):
                    '''
                    file that contains steps
                        steps_txt=file.txt
                            this is a text file that contains steps, just like command line.
                            steps can be in multiple lines.
                            multiple steps can be in a single line. (we use shell-like syntax)
                            there can be blank and comment lines (starting with #).
                        steps_py=file.py
                            this is a python file that contains steps, but is a python list of steps.
                    '''
                    file_type, file_name = m.groups()

                    steps2 = []
                    if file_type == 'txt':
                        with open(file_name) as fh:
                            # lines = fh.readlines()
                            # for line in lines:
                            #     # skip comment part of line
                            #     # for example,
                            #     #     # this is a comment
                            #     #     click_xpath=/a/b # this is a comment
                            #     #     css=#c # this is not a comment
                            #     if m := re.match(r"(.*?)\s(#.*?)", line):
                            #         # there is a comment at the end of the line; remove it.
                            #         line = m.group(1)
                            #     if m := re.match(r"#", line):
                            #         # comment starts at the beginning of the line; skip the whole line.
                            #         continue
                            #     if not line.strip():
                            #         # empty line; skip it.
                            #         continue
                                
                            #     # split the line using shell syntax
                            #     steps_in_this_line = shlex.split(line)
                            #     if debug:
                            #         print(f"follow2: parsed line={line} to {steps_in_this_line}")
                            #     steps2.extend(steps_in_this_line)
                            string = fh.read()
                            steps2 = tpsup.steptools_new.parse_steps(string, debug=debug)

                            print(f"follow2: parsed txt file {file_name} to steps2={steps2}")
                    else:
                        # file_type == 'py':
                        string = None
                        with open(file_name) as fh:
                            string = fh.read()
                        if not string:
                            print(f"file {file_name} is empty")
                        else:
                            try:
                                steps2 = eval(string)   
                            except Exception as e:
                                raise RuntimeError(f"failed to eval file {file_name}: {e}")
                            
                            # we expect the steps to be a list
                            if type(steps2) != list:
                                raise RuntimeError(f"steps in python file {file_name} is not a list")
                            
                            print(f"follow2: parsed py file {file_name} to steps2={steps2}")
                                
                    result = self.follow2(steps2, **opt)
                    if dryrun:
                        continue
                    if not result['Success']:
                        print(f"follow2: run steps_{file_type}={file_name} failed")
                        return result
                    continue

                if m := re.match(r"delay=(\d+)$", step):
                    delay = int(m.group(1))
                    print(f"follow2: delay={delay}")
                    if not dryrun:
                        self.delay = delay
                    continue

                # there are other string steps that are not related to block, we will handle them later.
            else:
                # for non-string step, here we only handle block related steps. non-block steps are handled later.
                if block_stack:
                    # we are in a block
                    block.append(step)
                    continue

            # now we are done with control block handling

            print()

            # # run debuggers['before']
            # for step in self.caller_globals['debuggers']['before']:
            #     # we don't care about the return value but we should avoid
            #     # using locator (step) that has side effect: eg, click, send_keys
            #     print(f"follow2: debug_before={step}")
            #     self.locate_f(step, **opt) 
            if 'debug' in self.usage_by_long:
                self.locate_f('debug=before', **opt)

            if self.delay:
                print(f"follow2: delay {self.delay} seconds before next step")
                time.sleep(self.delay)

            """
            non-control-block step can be a string or a more complex structure     

            complexity: string < dict (simple) < dict (parallel) < dict (chains)
            flexibility: string < dict (simple) < dict (parallel) < dict (chains)
        
            string 
                # string of a single locator, or multiple xpath/css/id separated by comma (searched in parallel).
                    xpath=/a/b, 
                    xpath=/a/c, 
                    'xpath=/a/b,xpath=/a/c' # search in parallel, if either one is found, we are good. 
                    click, 
                    dump, ...
                    note: only xpath/css/id can be in parallel (multiple locators separated by comma).

            # we could have also introduced 'list' for sequence flow, but sequence is already handled by follow2() interface.
            #     ['click_xpath=/a/b,click_xpath=/c/d', 'string="hello world"', 'dump']

            dict
                # dict are mainly for real locators, eg, xpath/css/id/iframe/shadow/tab. 
                # we use dict to introduce parallelism and if-then-else control.
                # other 'locators', eg, sleep, dump, wait, ... can be easily handled by string directly.
                {
                    # 'simple' allows you to handle parallelism and if-then-else control on top level.
                    'type': 'simple',
                    'action': {
                        'locator' : 'xpath=/a/b,xpath=/a/c', # 'simple' parallel, like the example on the left.
                                                            # 'simple' only means that syntax is simple.
                        #'Success' : 'code=print("found")', # optional. If either one is found, Do this. default is None
                        #'Failure' : 'print("not found")', # optional. If neither one is found, do this. default is RuntimeError
                    }
                },

                {
                    # 'parallel' allows you to handle individual path differently - define 'Success' and 'Failure' for each path.
                    'type': 'parallel',
                    'action': {
                        'paths' : [
                            {
                                'locator' : 'xpath=//dhi-wc-apply-button[@applystatus="true"]',
                                'Success': 'code=' + '''action_data['error'] = "applied previously"''', # optional. default is None
                            },
                            {
                                'locator' : 'xpath=//dhi-wc-apply-button[@applystatus="false"]',
                                'Success': 'click',
                            },
                        ],
                        # 'action' level 'Success' and 'Failure' are optional.
                        #'Success' : 'code=print("found")', # optional. If either one is found, Do this. default is None
                        #'Failure' : 'print("not found")', # optional. If neither one is found, do this. default is RuntimeError
                    }
                },
                
                {
                    # chain is a list of list of locators in parallel.
                    #     locators are in parallel, but the chain in each locator is in sequence.
                    #     locator in the chain can be parallel, eg, 'css=p,css=iframe'.
                    #     locator in chain can change dom, eg, 'iframe', 'shadow'.
                    # 'chains' is the only way that to archive dom change and parallelism at the same time.
                    'type': 'chains',          
                    'action': {
                        'paths' : [
                            {
                                'locator': [
                                    'xpath=/html/body[1]/ntp-app[1]', 'shadow',
                                    'css=#mostVisited', 'shadow',
                                    'css=#removeButton',
                                ],
                                'Success': 'code=print("found remove button")',
                            },
                            {
                                'locator': [
                                    'xpath=/html/body[1]/ntp-app[1]', 'shadow',
                                    'css=#mostVisited', 'shadow',
                                    'css=#actionMenuButton'
                                ],
                                'Success': 'code=print("found action button")',
                            },
                            # 'action' level 'Success' and 'Failure' are optional.
                            # 'Success': 'code=print("found")',
                            # 'Failure': 'print("not found")',
                        ],
                    },
                },
            ],

            'parallel' with a single path is the same as 'simple'.
            'chains' with a single path can be used to implement a 'sequence' of locators.

            'Success' and 'Failure' are optional. If not found, we raise RuntimeError by default.
            Therefore, define 'Failure' if you want to continue when not found.

            In 'parallel' and 'chains', we can define 'Success' and 'Failure' at 'action' level, but 
            we only define 'Success' at 'path' level, because the find...() function returns the first found element
            only. Therefore, we are not sure whether the other paths are found or not.

            we can make recurisve call of follow2() at 'Success' and 'Failure' to handle the next step; but
            that could make 'locator_driver' and 'driver_url' confusing.

            The design of non-control-block flow is: if...then if ... then if ... then ....

            """

            result = {'Success': False}

            print(f"follow2: running step={pformat(step)}")

            call_locate = True
            if dryrun:
                parsed = self.parse_and_check_input(step)
                if not parsed:
                    raise RuntimeError(f"failed to parse step '{step}'")
                
                usage_dict = parsed['usage_dict']
                if not usage_dict.get("has_dryrun", False):
                    # step cmd's function may have dryrun to check syntax. 
                    # if its usage_dict does have has_dryrun, we proceed to call the cmd with dryrun flag.
                    # if its usage_dict doesn't have has_dryrun, we can return here.
                    call_locate = False
            
            if call_locate:
                if interactive:
                    while True:
                        tpsup.interactivetools.hit_enter_to_continue()
                        try:
                            result = self.locate_f(step, **opt)
                            break
                        except Exception as e:
                            print(e)
                            # setting step_count to 0 is to make interactive mode to single step.
                            tpsup.interactivetools.nonstop_step_count = 0   
                else:
                    result = self.locate_f(step, **opt)

            # log_FileFuncLine(f"follow2: step={step} result={pformat(result)}")

            
            # for step in self.caller_globals['debuggers']['after']:
            #     # we don't care about the return value but we should avoid
            #     # using locator (step) that has side effect: eg, click, send_keys
            #     print(f"follow2: debug_after={step}")
            #     self.locate_f(step, **opt)
            if 'debug' in self.usage_by_long:
                self.locate_f('debug=after', **opt)

            if dryrun:
                continue
            
            if debug:
                print(f"follow2: result={pformat(result)}")

            if result is None:
                print(f"follow2: break, step={step} failed because result is None")
                ret['Success'] = False
                break
            
            # always check break_levels first, before check 'Success'. Because if break_levels > 0,
            # we should break the loop, no matter 'Success' is True or False.
            if result['break_levels']:
                print(f"follow2: break because step result break_levels={result['break_levels']} > 0")
                ret['break_levels'] = result['break_levels']
                break

            if result['continue_levels']:
                print(f"follow2: break because step result continue_levels={result['continue_levels']} > 0")
                ret['continue_levels'] = result['continue_levels']
                break

            # copy result to ret
            ret['Success'] = result['Success']

            # log_FileFuncLine(f"follow2: step={step} result={pformat(result)}")

            if not result['Success']:
                print(f"follow2: break, step={step} failed because result['Success'] is False")
                break
        
        # check for missing blockend
        if block_stack:
            raise RuntimeError(f"missing blockend. leftover block_stack={block_stack}.\n   for block={block}")
        return ret

    def follow(self, steps: list, **opt) -> dict:
        dryrun = opt.get('dryrun', 0)

        ret = ret0.copy()

        if not self.already_checked_syntax:
            # 1. checking syntax saves a lot time by spotting syntax error early!!!
            #    we call follow2() with dryrun=1 to check syntax
            # 2. batch.py can call this function repeatedly with batches of steps,
            #    but we only need to check syntax once (for one batch).
            opt2 = opt.copy()
            opt2['dryrun'] = 1
            opt2['debug'] = 0
            opt2['show_progress'] = 0
            opt2['interactive'] = 0
            opt2['verbose'] = 0

            print()
            print(f'follow: begin checking syntax')
            print(f"----------------------------------------------")
            result = self.follow2(steps, **opt2)
            print(f"----------------------------------------------")
            print(f'follow: end checking syntax - syntax looks good')
            print()
            self.already_checked_syntax = True

        if not dryrun:
            result = self.follow2(steps, **opt)
        
        ret.update(result)
        return ret

    def run_block(self, blockstart: str, negation: str,  condition: str, block: list, **opt):
        # we separate condition and negation because condition test may fail with exception, which is
        # neither True or False.  In this case, we want to know the condition test failed.
        debug = opt.get('debug', 0)
        dryrun = opt.get('dryrun', False)
        ret_init = {'Success': False, 'break_levels':0, 'continue_levels': 0, 'executed': None, 
                    # 'element': None
                    }

        if blockstart == 'while':
            while True:
                ret = ret_init.copy()

                result = self.if_block(negation, condition, block, **opt)

                if dryrun:
                    # avoid infinite while loop in dryrun which is to check syntax only
                    break

                if debug:
                    print(f"run_block: 1 while-loop result={result}")

                if not result['executed']:
                    # the block's condition is not met, we skip the block. we don't break.
                    print(f"run_block: while-loop failed at condition. we break")
                    break

                if result['executed'] == 'after-else':
                    # the block's condition is not met, we ran the after-else. we break.
                    print(f"run_block: while-loop failed at condition and ran after-else. we break")
                    break
       
                ret['executed'] = result['executed']
                ret['Success'] = result['Success']

                if result['break_levels']:
                    print(f"run_block: break_levels={result['break_levels']}, break the while loop")

                    # reduce break_levels by 1 because we really break a loop in while-loop block.
                    ret['break_levels'] = result['break_levels'] - 1
                    # '1' return 1 layer, '2' return 2 layers, ....
                    # we start with 0, meaning we are outside of any layer, no layer to return
                    # everytime we break out a layer (while loop), we decrease break_levels by 1.
                    # we allow break_levels greater than 1, so that we can break multiple layers,
                    # or even use it to implement 'return' in a function.

                    # only break the while-loop block, not the if block
                    break

                if result['continue_levels']:
                    print(f"run_block: continue the while loop")
                    # 'continue_levels' is consumed here (while-loop).
                    ret['continue_levels'] = result['continue_levels'] - 1

                    if ret['continue_levels'] > 0:
                        # we need to continue in parent while loop. so we break here
                        break
                    else:
                        # ret['continue_levels'] == 0:
                        continue
                
                if not result['Success']:
                    # even if the non-control-block failed, we should break the while loop.
                    # noramlly if non-control-block failed, an exception is raised.
                    break
        elif blockstart == 'if':
            ret = ret_init.copy()

            result=self.if_block(negation, condition, block, **opt)

            if debug:
                print(f"run_block: if_block result={result}")

            ret['Success'] = result['Success']
            ret['executed'] = result['executed']

            # propagate break_levels to outer layer; so do 'continue', because if-block doesn't consume
            # any break_levels or continue.
            ret['break_levels'] = result['break_levels']
            ret['continue_levels'] = result['continue_levels']
        else:
            raise RuntimeError(f"unsupported blockstart={blockstart}")

        return ret


    def if_block(self, negation: str,  condition: str, block: list, **opt):
        # we separate condition and negation because condition test may fail with exception, which is
        # neither True or False.  In this case, we want to know the condition test failed.

        dryrun = opt.get('dryrun', False)
        debug = opt.get('debug', 0)

        ret = {'Success': False, 'executed': None, 'break_levels': 0, 'continue_levels': 0, 
            #    'element': None
               }

        steps_by_type = split_by_else(block, **opt)
     
        for k, v in steps_by_type.items():
            print(f"if_block: {k} steps={v}")

        if not steps_by_type['before-else']:
            raise RuntimeError(f"if_block: missing before-else block")

        if not dryrun:
            # we should catch exception here, because the condition may fail with exception
            # and it should not be fatal
            try:
                condition_result = self.locate_f(condition, isExpression=True, **opt)
            except Exception as e:
                # we want to catch exception=unsupported 'locator=nosuch=1' in dryrun mode, so that 
                # we can catch syntax error in the condition.
                if 'unsupported' in str(e):
                    raise RuntimeError(f"if_block: condition={condition} test failed with exception={e}")
                print(f"if_block: condition={condition} test failed with exception={e}")
                condition_result = {'Success': False}

            # ret['executed'] indicates
            #     -  whether the before-else block (main block) 
            #     -  or after-else is executated.
            #     -  or None if the condition test failed.
            # if after-else doesn't exist, then ret['executed'] is None
            # this will also tell a while block whether to continue or break.
            if condition_result['Success'] and negation:
                to_execute_block = 'after-else'
                print(
                    f"if_not_block: condition '{condition}' is true, but negated, will execute {to_execute_block}")
            elif condition_result['Success'] and not negation:
                to_execute_block = 'before-else'
                print(f"if_block: condition '{condition}' is true, will execute {to_execute_block}")
            elif not condition_result['Success'] and not negation:
                to_execute_block = 'after-else'
                print(f"if_block: condition '{condition}' is not true, will execute {to_execute_block}")
            else:
                to_execute_block = 'before-else'
                print(f"if_not_block: condition '{condition}' is not true, but negated, will execute {to_execute_block}")
                
            if steps_by_type[to_execute_block]:
                # recursively calling follow2() to run the block
                # try:
                #     result = follow2(block, **opt)
                # except Exception as e:
                #     print(f"if_block: block part failed with exception={pformat(e)}")
                #     return ret

                # we should only catch exception in the condition part.
                # we should not catch the exception if the block part failed.
                result = self.follow2(steps_by_type[to_execute_block], **opt)

                if debug:
                    print(f"if_block: {to_execute_block} block result={result}")

                ret['Success'] = result['Success']
                ret['break_levels'] = result['break_levels']
                ret['continue_levels'] = result['continue_levels']
                ret['executed'] = to_execute_block
        else:
            # dryrun, for syntax check
            self.locate_f(condition, isExpression=True, **opt)
            self.follow2(steps_by_type['before-else'], **opt)

            if steps_by_type['after-else']:
                self.follow2(steps_by_type['after-else'], **opt)
        return ret
    
    def get_prompt(self) -> str:
        prompt = "\nAvailable commands: "
        for k in sorted(self.usage_by_long.keys()):
            v = self.usage_by_long[k]
            short = v.get('short', None)
            if short:
                prompt += f"{short}-{k} "
            else:
                prompt += f"{k} "
        prompt += " -- Enter command: "
        return prompt

    def parse_and_check_input(self, user_input: str) -> dict:
        '''
        parse user input and check it against usage_by_long_and_short
        '''
        # split user_input by 1st space or =.
        # command, arg, *_ = re.split(r'\s|=', user_input, maxsplit=1) + [None] * 2
        parsed = tpsup.steptools.parse_single_step(user_input)
        cmd = parsed['cmd']
        arg = parsed['arg']
        print(f"cmd='{cmd}', arg='{arg}'")
        if not cmd in self.usage_by_long_and_short:
            print(f"unknown command '{cmd}'")
            return None

        u:dict = self.usage_by_long_and_short[cmd]
        # print(f"usage dict: {pformat(u)}")
        if 'short_for' in u:
            # this is a short command, so map to its long command
            long_cmd = u['short_for']
            u = self.usage_by_long[long_cmd]
            # print(f"parsed input1: {pformat(parsed)}")

            # replace short cmd with long cmd in user_input
            #    l -> list
            #    ty=tylor -> type=tylor # not replace the 2nd 'ty'
            user_input = re.sub(rf"^{cmd}", f"{long_cmd}", user_input)
            cmd = long_cmd

        need_arg = u.get('need_arg', 0)
        no_arg = u.get('no_arg', False)

        if need_arg and not arg:
            print(f"cmd '{cmd}' needs arg")
            return None

        if no_arg and arg:
            print(f"cmd '{cmd}' doesn't need arg")
            return None
        
        parsed2 = {
            'cmd': cmd, # long command
            'arg': arg,
            'updated_user_input': user_input,
            'usage_dict': u,
        }

        return parsed2

    def explore(self, **opt):
        '''
        explore interactively
        '''
        prompt = self.get_prompt()

        while True:
            if self.display_f:
                self.display_f()

            while True:
                user_input = input(f"{prompt}: ")

                # result = self.locate_f(user_input, **opt)
                result = self.combined_locate(user_input, **opt)

                if result['break_levels']:
                    print(f"explore: break_levels={result['break_levels']}, bye")
                    return

                if not result['bad_input']:
                    break


    def combined_locate(self, user_input: str, **opt) -> dict:
        '''
        combined locate_f and handle common steps

        user input is
            command=[arg...]
        - command can be long or short form.
            t=hello world
            type=ello world
            help
            help=ype 
        '''
        ret = ret0.copy()

        if not isinstance(user_input, str):
            raise RuntimeError(f"combined_locate: user_input should be a string, not {type(user_input)}")
        
        # split user_input by 1st space or =.
        # command, arg, *_ = re.split(r'\s|=', user_input, maxsplit=1) + [None] * 2
        parsed = self.parse_and_check_input(user_input)
        # print(f"parsed input: {pformat(parsed)}")
        if not parsed:
            ret['bad_input'] = True
            return ret
        cmd = parsed['cmd']
        arg = parsed['arg']
        user_input = parsed['updated_user_input']

        if cmd == 'help':
            if arg is not None:
                if arg in self.usage_by_long_and_short:
                    print(f"help for '{arg}':")
                    print(self.usage_by_long[arg]['usage'])
                else:
                    print(f"unknown help topic '{arg}'")
            else:
                print("available commands:")
                for k in sorted(self.usage_by_long.keys()):
                    v = self.usage_by_long[k]
                    short = v.get('short', k)
                    print(f"{short}-{k}: {v.get('usage', '')}")
        elif cmd == "steps_txt":
            result = self.run_script(arg)
            ret.update(result) # update hash (dict) with hash (dict)
        elif cmd == 'steps_py':
            print(f"running python code: {arg}")
            try:
                exec(arg, globals(), locals())
            except Exception as e:
                print(f"Exception: {e}")
                ret['bad_input'] = True
        elif cmd == 'quit':
            print("bye")
            go_back = True
            ret['break_levels'] = 1
        # elif long_cmd == 'refresh':
        #     if not self.refresh_states_f:
        #         print("refresh_states_f is not defined")
        #         ret['bad_input'] = True
        #     else:
        #         print("refreshing the child window list tree...")
        #         self.refresh_states_f()
        #         self.refreshed = True
        # elif long_cmd == 'script':
        #     script_file = arg
        #     result = self.run_script(script_file)
        #     ret.update(result) # update hash (dict) with hash (dict)
        elif cmd == 'steps':
            print("enter multiple commands, one per line. end with END or ^D (Unix) or ^Z (Windows).")
            lines = []
            while True:
                try:
                    line = input()
                    if line == 'END':
                        break
                    lines.append(line)
                except EOFError:
                    break
            # print(f"you entered {len(lines)} lines: {lines}")
            one_string = "\n".join(lines)
            print(f"you entered:\n{one_string}")
            result = self.run_script(one_string)
            ret.update(result) # update hash (dict) with hash (dict)
        else:
            result = self.locate_f(user_input, **opt)
            ret.update(result) # update hash (dict) with hash (dict)

        return ret

    def run_script(self, script: str, **opt) -> dict:
        '''
        run a script file or a list of steps
        '''
        ret = ret0.copy()
        
        if not isinstance(script, str):
            raise RuntimeError(f"run_script: script should be a string, not {type(script)}")

        # remove leading spaces
        script = script.lstrip()
        if script.startswith("file="):
            # this is a file name
            file_name = script[len("file="):].strip()
            print(f"run_script: reading script from file {file_name}")
            try:
                with open(file_name) as fh:
                    script = fh.read()
            except Exception as e:
                print(f"run_script: failed to read script from file {file_name}: {e}")
                ret['Success'] = False
                ret['bad_input'] = True
                return ret
        parsed = []
        try:
            parsed = tpsup.steptools.parse_steps(script)
        except Exception as e:
            print(f"run_script: failed to parse script: {e}")
            ret['Success'] = False
            ret['bad_input'] = True
            return ret
        # steps are the 'original' of each parsed step.
        steps = [p['original'] for p in parsed]
        print(f"run_script: parsed script to {len(steps)} steps: {steps}")
        result = self.follow(steps, **opt)
        ret.update(result) # update hash (dict) with hash (dict)
        return ret

class Locator:
    '''
    Locator class is a wrapper of locate_cmd_arg() and locate_dict()
    '''
    def __init__(self, locate_cmd_arg: callable, locate_dict: callable):
        self.locate_cmd_arg = locate_cmd_arg
        self.locate_dict = locate_dict
        
    def locate(self, locator: Union[str, dict], **opt):
        """
        locate() is a wrapper of locate_cmd_arg() and locate_dict()
        if locator is a string, call locate_cmd_arg()
        if locator is a dict, call locate_dict()
        """
        if type(locator) == str:
            # locator should be a single step. single step will free us from worrying about
            # quotes in locator string.
            # for example,
            #     js=2element=document.querySelector("div[class='myclass']")
            # if we put it in a multi-step locator string, we need to escape the quotes.

            
            parsed = tpsup.steptools.parse_single_step(locator) 
            if not parsed:
                raise RuntimeError(f"failed to parse locator string={locator}") 
            cmd=parsed['cmd']
            arg=parsed['arg']
            
            return self.locate_cmd_arg(cmd, arg, **opt)
            # return self.locate(locator, **opt)
        elif type(locator) == dict:
            if 'cmd' in locator and 'arg' in locator:
                return self.locate_cmd_arg(locator['cmd'], locator['arg'], **opt)
            else:
                return self.locate_dict(locator, **opt)
        else:
            raise RuntimeError(f"unsupported locator type {type(locator)}, locator={pformat(locator)}")

def split_by_else(steps: list, **opt):
    '''
    split steps by 'else'.
    the 'else' shoule be outside of any if or while block.
    return 2 lists: steps1, steps2
    '''
    debug = opt.get('debug', 0)

    steps1=[]
    steps2=[]

    in_else = False
    blockend_stack = []


    for step in steps:
        if debug:
            print(f"split_by_else: step={pformat(step)}")

        step_type = type(step)

        if step_type == str:
            if blockend_stack:
            # we are in a block
                if step == blockend_stack[-1]:
                    # we found the expected blockend
                    blockend_stack.pop()
                elif m := re.match(r"\s*(end_while|end_if)$", step, flags=re.IGNORECASE):
                    # this is an unexpected blockend
                    raise RuntimeError(f"unexpected blockend={step}")
                if in_else:
                    steps2.append(step)
                else:
                    steps1.append(step)
                continue

            if m := re.match(r"\s*(while|if)(_not)?=(.+)", step, flags=re.IGNORECASE):
                # this is a nested block
                blockstart, negation, condition = m.groups()
                blockend = f"end_{blockstart}"
                blockend_stack.append(blockend)
                if in_else:
                    steps2.append(step)
                else:
                    steps1.append(step)
                continue

            elif not blockend_stack and step == 'else':
                # we found 'else' outside of any block.
                # we only take action on 'else' when we are not in a block.
                if in_else:
                    raise RuntimeError(f"multiple 'else' found")
                in_else = True
                continue
                
            else:
                if in_else:
                    steps2.append(step)
                else:
                    steps1.append(step)
                continue
        else:
            if in_else:
                steps2.append(step)
            else:
                steps1.append(step)
            continue

    if blockend_stack:
        raise RuntimeError(f"missing blockend={blockend_stack[-1]}")
    
    steps_by_type = {
        'before-else': steps1,
        'after-else': steps2,
    }
    
    return steps_by_type       
    

def decoded_get_defined_locators(locate_func: callable, **opt):
    '''
    get list of locators in locate() function.
    we first get the source code of locate() function, then we extract the locators
    from 'if' and 'elif' statements.    
    '''
    import inspect
    import re

    source = inspect.getsource(locate_func)
    # print(f"source={source}")

    locators = []
    # extract all the 'if' and 'elif' statements from the source code
    # we use re.DOTALL to match newline
    for m in re.finditer(r"^    (if|elif) (m :=.+?locator)", source, re.MULTILINE | re.DOTALL):

        locators.append(m.group(2))
    for m in re.finditer(r"^    (if|elif) (locator == .+?):", source, re.MULTILINE | re.DOTALL):
        locators.append(m.group(2))

    return locators


def handle_break(step: str, **opt):
    '''
    handle break and continue
    '''
    debug = opt.get('debug', 0)
    dryrun = opt.get('dryrun', 0)

    ret = {'break_levels': 0, 'continue_levels': 0,}
    
    '''
    example of steps:
        break       # this is default to break=1, ie, break one level of while loop.
        break=2     # break two levels of while loop. 
                    # we can use this archieve "goto" effect.
        last        # this is the same as 'break'

        continue    # break the current loop. then continue with the next while loop
        continue=2  # break the current while loop and the parent while loop. then
                    # continue with the next parent while loop.
                    # we can use this archieve "goto" effect.
        next        # this is the same as 'continue'

        return      # this is the same as 'break=1000'

        exit        # this is the same as 'exit=0'
        exit=1      # this is the same as 'exit=1'
    '''

    # handle shorcut
    if step == 'break' or step == 'last':
        step = 'break=1'
    elif step == 'continue' or step == 'next':
        step = 'continue=1'
    elif step == 'return':
        step = 'break=1000'
    elif step == 'exit':
        step = 'exit=0'

    if m := re.match(r"break=(\d+)", step):
        count = int(m.group(1))
        print(f"handle_break: break_levels={count}")
        if not dryrun:
            ret['break_levels'] = count
    elif m := re.match(r"continue=(\d+)", step):
        count = int(m.group(1))
        print(f"handle_break: continue={count}")
        if not dryrun:
            ret['continue_levels'] = count
    elif m := re.match(r"exit=(\d+)", step):
        exit_code = m.group(1)
        if not exit_code:
            exit_code = 0
        else:
            exit_code = int(exit_code)
        print(f"handle_break: exit with code {exit_code}")
        if not dryrun:
            exit(exit_code)
    else:
        '''
        the goodness of returning None is that we add handle_break() into the elif chain.
            if ....
                 ...
            elif ...
                ...
            elif result := handle_break(step, **opt):
                 ...
        '''
        # no match
        return None
  
    return ret





def main():
    # start_http_server(port=8000, debug=1)
    time.sleep(2)
    # stop_http_server(port=8000, debug=1)

if __name__ == "__main__":
    main()
        



    
