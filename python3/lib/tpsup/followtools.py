import inspect
from pprint import pformat
import re
import shlex

class FollowEnv:
    def __init__(self,
                 str_action: callable=None,
                 dict_action: callable=None,
                 **opt):
        self.str_action = str_action
        self.dict_action = dict_action

        self.caller_globals = inspect.currentframe().f_back.f_globals
        self.caller_locals = inspect.currentframe().f_back.f_locals
        self.break_levels = 0
        self.already_checked_syntax = False

    def follow(self, steps: list,  **opt):
        '''
        follow() is a recursive. it basic flow is: if ... then if ... then if ... then ...
        for example: [ 'click_xpath=/a/b', '"iframe', 'click_xpath=/c/d', 'string="hello world"', 'dump' ]
        By default, if any 'if' failed, we stop. For example, if 'click_xpath=/a/b' failed, we stop.
        If any 'then if' failed, we stop. For example, if 'iframe' failed, we stop.

        as of now, we only allow follow() to be recursive on block-statement (if/while) level; once
        follow() calls locate(), locate() will not call follow(). This is to avoid infinite recursion.
        '''

        debug = opt.get("debug", 0)
        dryrun = opt.get("dryrun", 0)

        # we support single-level block, just for convenience when testing using appium_steps
        # we don't support nested blocks; for nested block, use python directly
        block = []
        expected_blockend = None

        # use this to detect nested block of the same type, for example
        #     if      # if block depth = 1
        #         if      # if block depth = 2
        #         end_if  # if block depth = 1
        #         while   # while block depth = 1, if block depth = 1
        #         end_while # while block depth = 0, if block depth = 1
        #     end_if      # if block depth = 0

        block_depth = 0 # this needs to be a local var as follow() is recursive.

        condition = None
        blockstart = None
        negation = False

        ret = {'Success': False}

        if not steps:
            print(f'follow: steps are empty. return')
            return

        for step in steps:
            if debug:
                print(f"follow: step={pformat(step)}")

            step_type = type(step)

            # first handle control block. block start and block end are strings only.
            if block_depth > 0:
                # we are in a block
                
                if step_type == str and step == expected_blockend:
                    # step matches the expected blockend
                    block_depth -= 1

                    if block_depth == 0:
                        # the outermost block is ended; we didn't run the block yet.
                        if debug:
                            print(f"follow: matched expected_blockend={expected_blockend}")
                        expected_blockend = None

                        print(f"follow: run block={block}, condition={condition}, block_depth={block_depth}")
                        if not block:
                            raise RuntimeError(f"block is empty")
                    
                        # run_block() recursively calls follow()
                        result = self.run_block(blockstart, negation,
                                    condition, block, **opt)                    
                        if dryrun:
                            # we only check syntax, therefore, we don't check the result and move on
                            continue

                        if not result['Success']:
                            print(f"follow: break because block failed.")
                            # if the block failed, we stop
                            break
                    else:
                        # we only encountered a nested block end
                        if debug:
                            print(f"follow: matched expected_blockend={expected_blockend}, but still in block_depth={block_depth}")

                        # we keep the nested block end in the block, so that we can recursively call run_block()
                        block.append(step)
                else:
                    # this is not the expected blockend, we keep it in the block.
                    block.append(step)

                # we are still in a block; we continue until we find the expected blockend.
                # we only build the block, we don't run it.
                # we will run the block after we find the expected blockend.
                continue
            
            # now that we are not in a block, we check whether this step is a start of a block
            if step_type == str:
                if m := re.match(r"\s*(while|if)(_not)?=(.+)", step):
                    # we are starting a new block
                    block_depth += 1
                    blockstart = m.group(1)
                    negation = m.group(2)
                    condition = m.group(3)

                    if negation:
                        expected_blockend = f"end_{blockstart}{negation}"
                    else:
                        expected_blockend = f"end_{blockstart}"
                    block = []
                    if debug:
                        print(f"follow: blockstart={blockstart}, negation={negation}, condition={condition}, "
                            f"expected_blockend={expected_blockend}, block_depth={block_depth}")
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
                            lines = fh.readlines()
                            for line in lines:
                                # skip comment part of line
                                # for example,
                                #     # this is a comment
                                #     click_xpath=/a/b # this is a comment
                                #     css=#c # this is not a comment
                                if m := re.match(r"(.*?)\s(#.*?)", line):
                                    # there is a comment at the end of the line; remove it.
                                    line = m.group(1)
                                if m := re.match(r"#", line):
                                    # comment starts at the beginning of the line; skip the whole line.
                                    continue
                                if not line.strip():
                                    # empty line; skip it.
                                    continue
                                
                                # split the line using shell syntax
                                steps_in_this_line = shlex.split(line)
                                if debug:
                                    print(f"follow: parsed line={line} to {steps_in_this_line}")
                                steps2.extend(steps_in_this_line)

                            print(f"follow: parsed txt file {file_name} to steps2={steps2}")
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
                            
                            print(f"follow: parsed py file {file_name} to steps2={steps2}")
                                
                    result = self.follow(steps2, **opt)
                    if dryrun:
                        continue
                    if not result['Success']:
                        print(f"follow: run steps_{file_type}={file_name} failed")
                        return result
                    continue
            # now we are done with control block handling

            print()

            # # run debuggers['before']
            # for step in self.caller_globals['debuggers']['before']:
            #     # we don't care about the return value but we should avoid
            #     # using locator (step) that has side effect: eg, click, send_keys
            #     print(f"follow: debug_before={step}")
            #     self.str_action(step, **opt) 
            self.str_action('debug_before', **opt)

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

            # we could have also introduced 'list' for sequence flow, but sequence is already handled by follow() interface.
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

            we can make recurisve call of follow() at 'Success' and 'Failure' to handle the next step; but
            that could make 'locator_driver' and 'driver_url' confusing.

            The design of non-control-block flow is: if...then if ... then if ... then ....

            """

            result = {'Success': False}

            if step_type == str:
                result = self.str_action(step, **opt)
            elif step_type == dict:
                need_driver = True # all dict locators need driver
                result = self.dict_action(step, **opt)
            else:
                raise RuntimeError(f"unsupported step type={step_type}, step={pformat(step)}")
            
            # for step in self.caller_globals['debuggers']['after']:
            #     # we don't care about the return value but we should avoid
            #     # using locator (step) that has side effect: eg, click, send_keys
            #     print(f"follow: debug_after={step}")
            #     self.str_action(step, **opt)
            self.str_action('debug_after', **opt)

            if dryrun:
                continue
            
            if debug:
                print(f"follow: result={pformat(result)}")

            if result is None:
                print(f"follow: break, step={step} failed because result is None")
                ret['Success'] = False
                break

            # copy result to ret
            ret['Success'] = result['Success']

            if not result['Success']:
                print(f"follow: break, step={step} failed because result['Success'] is False")
                break

            # check break_levels in result
            if 'break_levels' in result:
                self.break_levels = result['break_levels']
                ret['break_levels'] = self.break_levels

            if self.break_levels:
                print(f"follow: break because break_levels={self.break_levels} > 0")
                # reduce break_levels by 1
                self.break_levels = self.break_levels - 1
                break
        
        return ret

    def check_syntax_then_follow(self, steps: list, **opt):
        dryrun = opt.get('dryrun', 0)

        if not self.already_checked_syntax:
            # 1. checking syntax saves a lot time by spotting syntax error early!!!
            #    we call follow() with dryrun=1 to check syntax
            # 2. batch.py can call this function repeatedly with batches of steps,
            #    but we only need to check syntax once (for one batch).
            opt2 = opt.copy()
            opt2['dryrun'] = 1
            opt2['debug'] = 0
            opt2['show_progress'] = 0
            opt2['interactive'] = 0
            opt2['verbose'] = 0

            print()
            print(f'begin checking syntax')
            print(f"----------------------------------------------")
            result = self.follow(steps, **opt2)
            print(f"----------------------------------------------")
            print(f'end checking syntax - syntax looks good')
            print()
            self.already_checked_syntax = True

        if not dryrun:
            self.follow(steps, **opt)

    def run_block(self, blockstart: str, negation: str,  condition: str, block: list, **opt):
        # we separate condition and negation because condition test may fail with exception, which is
        # neither True or False.  In this case, we want to know the condition test failed.
        debug = opt.get('debug', 0)
        dryrun = opt.get('dryrun', False)
        ret = {'Success': False, 'executed': False, 'element': None}

        if blockstart == 'while':
            while True:
                result = self.if_block(negation, condition, block, **opt)
                if debug:
                    print(f"run_block: result={result}")
                if not result['executed']:
                    break

                # check break_levels in result
                if 'break_levels' in result:
                    self.break_levels = result['break_levels']
                    ret['break_levels'] = self.break_levels

                # only while-loop can be broken.
                if self.break_levels:
                    if debug:
                        print(f"run_block: break_levels={self.break_levels}, break the while loop")
                    # reduce break_levels by 1
                    self.break_levels = self.break_levels - 1
                    break
                if dryrun:
                    # avoid infinite while loop in dryrun
                    break
        elif blockstart == 'if':
            result=self.if_block(negation, condition, block, **opt)
        else:
            raise RuntimeError(f"unsupported blockstart={blockstart}")

        ret['Success'] = result['Success']
        ret['executed'] = result['executed']

        return ret


    def if_block(self, negation: str,  condition: str, block: list, **opt):
        # we separate condition and negation because condition test may fail with exception, which is
        # neither True or False.  In this case, we want to know the condition test failed.

        dryrun = opt.get('dryrun', False)

        ret = {'Success': False, 'executed': False}

        if not dryrun:
            # we should catch exception here, because the condition may fail with exception
            # and it should not be fatal
            try:
                result = self.str_action(condition, isExpression=True, **opt)
            except Exception as e:
                # we want to catch exception=unsupported 'locator=nosuch=1' in dryrun mode, so that 
                # we can catch syntax error in the condition.
                if dryrun and 'unsupported' in str(e):
                    raise RuntimeError(f"if_block: condition={condition} test failed with exception={e}")
                print(f"if_block: condition={condition} test failed with exception={e}")
                result = {'Success': False}
        
            if result['Success'] and negation:
                print(
                    f"if_not_block: condition '{condition}' is true, but negated, block is not executed")
                to_execute_block = False
            elif result['Success'] and not negation:
                print(f"if_block: condition '{condition}' is true, block is executed")
                to_execute_block = True
            elif not result['Success'] and not negation:
                print(f"if_block: condition '{condition}' is not true, block is not executed")
                to_execute_block = False
            else:
                print(f"if_block: condition '{condition}' is not true, but negated, block is executed")
                to_execute_block = True

            ret['executed'] = to_execute_block

            if to_execute_block:
                # recursively calling follow() to run the block
                # try:
                #     result = follow(block, **opt)
                # except Exception as e:
                #     print(f"if_block: block part failed with exception={pformat(e)}")
                #     return ret

                # we should only catch exception in the condition part.
                # we should not catch the exception if the block part failed.
                result = self.follow(block, **opt)

                if result and not dryrun:
                    ret['Success'] = result['Success']
        else:
            # dryrun
            self.str_action(condition, isExpression=True, **opt)  
            self.follow(block, **opt)
        return ret
