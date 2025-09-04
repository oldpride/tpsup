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
import tpsup.steptools

class Explorer:
    def __init__(self,
                 locate_f: callable,
                 display_f: callable = None,
                 refresh_states_f: callable = None,
                 app_usage_by_long: dict = None,
                 **opt):
        
        self.locate_f = locate_f
        if not callable(self.locate_f):
            raise TypeError("locate_f must be a callable function")
        
        self.display_f = display_f
        self.refresh_states_f = refresh_states_f

        self.refreshed = False
        # after each refresh_states_f, we set refreshed to True.
        # after each display_f, we set refreshed to False.

        self.ret0 = {
            'break': False, # break the current loop or script
            'bad_input': False, # bad input
        }

        self.usage_by_long = {
            'help': {
                'short': 'h',
                # can have or not have arg
                'usage': '''
                    h
                    h=type
                ''',
            },
            'python': {
                'short': 'py',
                'need_arg': True,
                'usage': '''
                    run a python code.
                    py=print("hello world")
                    py=dump_window(current_window)
                    py=print(dir(current_window))
                    py=print(current_window.__dict__)
                ''',
            },
            'quit': {
                'short': 'q',
                'no_arg': True,
                'usage': '''
                    q
                ''',
            },
            'script': {
                'short': 'sc',
                'need_arg': True,
                'usage': '''
                    sc=script.txt
                    script.txt contains multiple commands, one per line.
                    eg:
                    sc=mymodule.py
                    where mymodule.py contains:
                    c=9
                    c=30
                    ''',
            },
            'steps': {
                'short': 'st',
                'no_arg': True,
                'usage': '''
                    st

                    you can enter multiple commands, one per line. 
                    end with END or ^D (Unix) or ^Z (Windows).
                    example:
                        st
                        c=9
                        c=30
                        END
                ''',
            },
        }

        # if app_usage_by_long is defined, merge it.
        if app_usage_by_long:
            self.usage_by_long.update(app_usage_by_long)

        self.usage_by_short = {}
        for k, v in self.usage_by_long.items():
            short = v.get('short', None)
            if short:
                self.usage_by_short[short] = v
                self.usage_by_short[short]['long'] = k
            v['long'] = k # add long name to each usage item

    def run_script(self, script: Union[str, list], **opt):
        '''
        if script is a string, it is a file name.
        if script is a list,   it is a list of steps
        '''
        debug = opt.get('debug', False)

        if isinstance(script, str):
            with open(script, 'r') as f:
                bigstring = f.readlines()
        elif isinstance(script, list):
            bigstring = script
        else:
            raise TypeError("script must be a string or a list")
        
        ret = self.ret0.copy()

        steps = tpsup.steptools.parse_steps('\n'.join(bigstring), debug=debug)

        for s in steps:
            print(f"running step = {pformat(s)}")
            result = self.combined_locate(s, **opt)

            go_back = result.get('break', False)
            # everytime before we display, we refresh states.
            # therefore, redisplay and refresh_state are linked.
            redisplay = result.get('redisplay', False) 

            if redisplay and self.refresh_states_f:
                # before redisplaying, we refresh states.
                self.refresh_states_f(**opt)
            if go_back:
                print("script terminated by quit command")
                break

            ret.update(result) # update hash (dict) with hash (dict)

        return ret

    
    def get_prompt(self) -> str:
        prompt = ""
        for k in sorted(self.usage_by_long.keys()):
            v = self.usage_by_long[k]
            short = v.get('short', k)
            prompt += f"{short}-{k} "
        return prompt


    def explore(self, **opt):
        '''
        explore interactively.
        '''

        debug = opt.get("debug", 0)
        dryrun = opt.get("dryrun", 0)

        script = opt.get('script', None)
        if script:
            print(f"running script file: {script}")
            result = self.run_script(script, **opt)
            if result.get('break', False):
                return

        while True:
            # everytime before we display, we refresh states.
            # therefore, redisplay and refresh_state are linked.
            if not self.refreshed and self.refresh_states_f:
                print("refreshing the child window list tree...")
                self.refresh_states_f()
                self.refreshed = True

            if self.display_f:
                self.display_f()

            # after display, we set refreshed to False.
            self.refreshed = False

            while True: # loop until we get valid input
                prompt = self.get_prompt()
                user_input = input(f"{prompt}: ")

                result = self.combined_locate(user_input, **opt)

                if result.get('break', False):
                    print("bye")
                    return
                
                if self.refreshed:
                    # if refreshed, break to outer loop to redisplay
                    break
                

    def combined_locate(self, user_input: Union[str, dict], **opt) -> dict:
        '''
        user input is
            command=[arg...]
        - command can be long or short form.
            t=hello world
            type=ello world
            help
            help=ype 
        '''
        ret = self.ret0.copy()

        if isinstance(user_input, dict):
            # already parsed
            cmd = user_input['cmd']
            arg = user_input['arg']
        elif isinstance(user_input, str):
            # split user_input by 1st space or =.
            # command, arg, *_ = re.split(r'\s|=', user_input, maxsplit=1) + [None] * 2
            parsed = tpsup.steptools.parse_single_step(user_input)
            cmd = parsed['cmd']
            arg = parsed['arg']
        print(f"cmd='{cmd}', arg='{arg}'")
        if cmd in self.usage_by_short:
            v = self.usage_by_short.get(cmd, None)
        else:
            v = self.usage_by_long.get(cmd, None)

        if v is None:
            print(f"unknown cmd '{cmd}'")
            ret['bad_input'] = True
            return ret

        long_cmd = v['long']

        need_arg = v.get('need_arg', 0)
        no_arg = v.get('no_arg', False)

        if need_arg and not arg:
            print(f"cmd '{cmd}' needs arg")
            ret['bad_input'] = True
            return ret
        elif no_arg and arg:
            print(f"cmd '{cmd}' doesn't need arg")
            ret['bad_input'] = True
            return ret

        if long_cmd == 'script':
            self.run_script(arg)
        elif long_cmd == 'help':
            if arg is not None:
                if arg in self.usage_by_long:
                    print(f"help for '{arg}':")
                    print(self.usage_by_long[arg]['usage'])
                elif arg in self.usage_by_short:
                    long_name = self.usage_by_short[arg]['long']
                    print(f"help for '{arg}' ({long_name}):")
                    print(self.usage_by_long[long_name]['usage'])
                else:
                    print(f"unknown help topic '{arg}'")
            else:
                print("available commands:")
                for k in sorted(self.usage_by_long.keys()):
                    v = self.usage_by_long[k]
                    short = v.get('short', k)
                    print(f"{short}-{k}: {v.get('usage', '')}")
        elif long_cmd == 'python':
            print(f"running python code: {arg}")
            try:
                exec(arg, globals(), locals())
            except Exception as e:
                print(f"Exception: {e}")
                ret['bad_input'] = True
        elif long_cmd == 'quit':
            print("bye")
            go_back = True
            ret['break'] = True
        elif long_cmd == 'refresh':
            if not self.refresh_states_f:
                print("refresh_states_f is not defined")
                ret['bad_input'] = True
            else:
                print("refreshing the child window list tree...")
                self.refresh_states_f()
                self.refreshed = True
        elif long_cmd == 'script':
            script_file = arg
            result = self.run_script(script_file)
            ret.update(result) # update hash (dict) with hash (dict)
        elif long_cmd == 'steps':
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
            print(f"you entered {len(lines)} lines: {lines}")
            result = self.run_script(lines)
            ret.update(result) # update hash (dict) with hash (dict)
        else:
            result = self.locate_f(long_cmd, arg, self.ret0, **opt)

            ret.update(result) # update hash (dict) with hash (dict)

        return ret

def main():
    pass

if __name__ == "__main__":
    main()
        



    
