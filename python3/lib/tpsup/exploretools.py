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
                # can have or not have args
                'usage': '''
                    h
                    h type
                ''',
            },
            'python': {
                'short': 'py',
                'need_args': True,
                'usage': '''
                    run a python code.
                    py print("hello world")
                    py dump_window(current_window)
                    py print(dir(current_window))
                    py print(current_window.__dict__)
                ''',
            },
            'quit': {
                'short': 'q',
                'no_args': True,
                'usage': '''
                    q
                ''',
            },
            'script': {
                'short': 'sc',
                'need_args': True,
                'usage': '''
                    sc script.txt
                    script.txt contains multiple commands, one per line.
                    eg:
                    sc myscript.txt
                    where myscript.txt contains:
                    c 9
                    c 30
                    ''',
            },
            'steps': {
                'short': 'st',
                'no_args': True,
                'usage': '''
                    st

                    you can enter multiple commands, one per line. 
                    end with END or ^D (Unix) or ^Z (Windows).
                    example:
                        st
                        c 9
                        c 30
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

        for k, v in steps:
            print(f"running command: '{k}={v}'")
            result = self.combined_locate(f"{k}={v}", **opt)

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


    def run_script_line_by_line(self, script: Union[str, list], **opt):
        '''
        if script is a string, it is a file name.
        if script is a list,   it is a list of steps
        '''
        debug = opt.get('debug', False)

        if isinstance(script, str):
            with open(script, 'r') as f:
                lines = f.readlines()
        elif isinstance(script, list):
            lines = script
        else:
            raise TypeError("script must be a string or a list")
        
        ret = self.ret0.copy()

        for line in lines:
            # remove the trailing newline
            line = line.rstrip('\n')
            line = line.rstrip('\r') # in case of Windows line ending
            
            # skip empty lines and comment lines
            if re.match(r'^\s*$', line):
                continue
            if re.match(r'^\s*#', line):
                continue

            print(f"running command: '{line}'")
            result = self.combined_locate(line, **opt)

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
                # # get user input
                # if self.prompt_f:
                #     prompt = self.prompt_f()
                # else:
                #     prompt = "command"
                # user_input = input(f"{prompt}: ")

                prompt = self.get_prompt()
                user_input = input(f"{prompt}: ")

                result = self.combined_locate(user_input, **opt)

                if result.get('break', False):
                    print("bye")
                    return
                
                if self.refreshed:
                    # if refreshed, break to outer loop to redisplay
                    break
                

    def combined_locate(self, user_input: str, **opt) -> dict:
        '''
        user input is
            command [args...]
        - there is 1 single space between command and args.
        - args can have front and trailing spaces. 
        - command can be long or short form.
            t hello world
            type hello world
            h type
            help type 
        '''
        ret = self.ret0.copy()

        # split user_input by 1st space or =.
        command, args, *_ = re.split(r'\s|=', user_input, maxsplit=1) + [None] * 2
        print(f"command='{command}', args='{args}'")
        if command in self.usage_by_short:
            v = self.usage_by_short.get(command, None)
        else:
            v = self.usage_by_long.get(command, None)

        if v is None:
            print(f"unknown command '{command}'")
            ret['bad_input'] = True
            return ret

        long_cmd = v['long']

        need_args = v.get('need_args', 0)
        no_args = v.get('no_args', False)

        if need_args and not args:
            print(f"command '{command}' needs args")
            ret['bad_input'] = True
            return ret
        elif no_args and args:
            print(f"command '{command}' doesn't need args")
            ret['bad_input'] = True
            return ret

        if long_cmd == 'script':
            self.run_script(args)
        elif long_cmd == 'help':
            if args is not None:
                if args in self.usage_by_long:
                    print(f"help for '{args}':")
                    print(self.usage_by_long[args]['usage'])
                elif args in self.usage_by_short:
                    long_name = self.usage_by_short[args]['long']
                    print(f"help for '{args}' ({long_name}):")
                    print(self.usage_by_long[long_name]['usage'])
                else:
                    print(f"unknown help topic '{args}'")
            else:
                print("available commands:")
                for k in sorted(self.usage_by_long.keys()):
                    v = self.usage_by_long[k]
                    short = v.get('short', k)
                    print(f"{short}-{k}: {v.get('usage', '')}")
        elif long_cmd == 'python':
            print(f"running python code: {args}")
            try:
                exec(args, globals(), locals())
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
            script_file = args
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
            result = self.locate_f(long_cmd, args, self.ret0, **opt)

            ret.update(result) # update hash (dict) with hash (dict)

        return ret

def main():
    pass

if __name__ == "__main__":
    main()
        



    
