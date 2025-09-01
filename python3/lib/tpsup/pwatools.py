import io
import re
import sys
from time import sleep
import pywinauto
from pywinauto.application import Application, WindowSpecification
from pywinauto.controls.uiawrapper import UIAWrapper
from tpsup.cmdtools import run_cmd

from typing import Union
import tpsup.exploretools

def dump_window(o: Union[WindowSpecification, UIAWrapper], app: Application = None) -> None:
    print(f"\ninput's python class name={type(o).__name__}")

    d = {
        'window': None,
        'wrapper': None,
    }
    
    if isinstance(o, WindowSpecification):
        d['window'] = o
        d['wrapper'] = o.wrapper_object()
    elif isinstance(o, UIAWrapper):
        d['wrapper'] = o
        window_handle = o.handle
        if app is not None:
            d['window'] = app.window(handle=window_handle)
        else:
            raise ValueError("app must be provided if o is a UIAWrapper")
    else:
        raise TypeError(f"Expected WindowSpecification or UIAWrapper, got {type(o)}")

    for k in ['window', 'wrapper']:
        x= d[k]
        print(f"{k}'s python class name={type(x).__name__}")

    print("\n")
    for k in ['window', 'wrapper']:
        x= d[k]
        # if window_text() method exists, print it
        if hasattr(x, "window_text"):
            if callable(x.window_text):
                print(f"{k}'s window_text={x.window_text()}")
            else:
                print(f"{k}'s window_text is not callable")
        else:
            print(f"{k}'s window_text does not exist")

    for k in ['window', 'wrapper']:
        x= d[k]
        # to lookup wrapper, we have to explicitly use wrapper
        print(f"\n{k}.__dict__ = {x.__dict__}\n")

    for k in ['window', 'wrapper']:
        x= d[k]
        print(f"\ndir({k}) = {dir(x)}")

    for k in ['window', 'wrapper']:
        x= d[k]
        if hasattr(x, 'print_control_identifiers' ):
            if callable(x.print_control_identifiers):
                print(f"\n{k}.print_control_identifiers()=")
                print(f"{x.print_control_identifiers()}")
            else:
                print(f"{k}.print_control_identifiers() is not callable")
        else:
            print(f"{k}.print_control_identifiers() does not exist")
    
    for k in ['window', 'wrapper']:
        x= d[k]
        print(f"\n{k}'s child windows")
        for w in x.children():
            print(f"{k}'s child window={w}, title={w.window_text()}, python={type(w).__name__}, class_name={w.class_name()}")




class PwaEnv:
    def __init__(self, 
                 **opt):
        
        self.app: Application = opt.get('app', None)
        self.title_re: str = opt.get('title_re', None)
        self.window_and_child_specs = []
        self.top_window = None
        self.current_window = None
        self.init_steps = opt.get('init_steps', [])
        
        # # one of these must be provided: app, title_re
        # if not (self.app or self.title_re):
        #     raise ValueError("Either app or title_re must be provided")
        
        self.backend = opt.get('backend', 'uia')

        if not self.app:
            self.app = Application(
                # backend="win32", # win32 is the default.
                # backend="uia", # uia is modern and preferred.
                backend=self.backend,
            )
        
    usage = {
        'start': {
            'short': 'start',
            'need_args': True,
            'usage': '''
                start=notepad.exe
                start="C:\\Program Files\\Mozilla Firefox\\firefox.exe"
                start="C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
                s="C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
                ''',
        },
        'connect': {
            'short': 'conn',
            'need_args': True,
            'usage': '''
                connect with title_re
                conn=".*tianjunk.*"
                ''',
        },
        'child': {
            'short': 'c',
            'need_args': True,
            'usage': '''
                c=1
                ''',
        },
        'control_identifiers': {
            'short': 'ci',
            'no_args': True,
            'usage': '''
                get the control identifiers of the current window
                ci
            ''',
        },
        'refresh': {
            'short': 'r',
            'no_args': True,
            'usage': '''
                refresh the child window list
                r
            ''',
        },
        'text': {
            'short': 'tx',
            'no_args': True,
            'usage': '''
                get the text of the current window
                tx
            ''',
        },
        'top' : {
            'short': 'top',
            'no_args': True,
            'usage': '''
                get the top window
                top
            ''',
        },
        'type': {
            'short': 'ty',
            'need_args': 1,
            'usage': '''
                ty=hello
                ty="hello world"
                ty={UP}
                ty={ENTER}
                ty={F5}
            ''',
        },
    }
       
    # def start(self, cmd1: str, **opt) -> Application:
    #     print(f"startup command: {cmd1}")
    #     # self.app.start(cmd1, wait_for_idle=False)
    #     self.app.start(cmd1)
    #     sleep(2)  # wait for the app to start

            
    #         if self.top_window is None:
    #                         cmd1 = opt.get('command1', None)
    #         if cmd1:
    #             self.start(cmd1, **opt)
    #             self.app.connect(title_re=self.title_re, timeout=10)
    #             print(f"connected")
    #             self.top_window = self.app.top_window() # now it should work

    #         self.current_window = self.top_window
    #     else:
    #         # without cmd1, we can only connect to an existing app window.
    #         self.app = Application(
    #             # backend="win32", # win32 is the default.
    #             # backend="uia", # uia is modern and preferred.
    #             backend=backend,
    #         )

    #         print(f"Connecting app with title_re=\"{self.title_re}\"...")           
    #         connected = False
    #         try:
    #             self.app.connect(title_re=self.title_re, timeout=10)
    #             print("connected")
    #             connected = True
    #         except Exception as e:
    #             print(f"Failed to connect to app: {e}")

    #         if not connected:
    #             # try to start it
    #             cmd2 = opt.get('command2', None)
    #             if cmd2:
    #                 print(f"Starting app with command: {cmd2}")
    #                 # run_cmd(cmd2)
    #                 self.app.start(cmd2, wait_for_idle=False)
    #                 sleep(2) # wait for the app to start
    #                 # print(f"connecting app with title_re=\"{title_re}\"...")
    #                 # self.app.connect(title_re=self.title_re, timeout=10)
    #             else:
    #                 print(f"No startup command provided.")
    #                 return None

    #         self.top_window = self.app.top_window()
    #         self.current_window = self.top_window

    #     print(f"\nexplore_app input's python class name={type(self.app).__name__}")            
    #     print(f"top_window's python class name={type(self.top_window).__name__}")

    #     self.top_window.wait('visible')
    #     self.top_window.click_input()  # ensure the window is focused
    #     sleep(1)
    #     return self.app

    def get_windowspec_from_uiawrapper(self, u: UIAWrapper) -> WindowSpecification:
        '''
        get the WindowSpecification from a UIAWrapper.
        '''
        handle = u.handle
        w:WindowSpecification = self.app.window(handle=handle)
        return w

    def get_control_identifiers(self, o: Union[WindowSpecification, UIAWrapper]) -> str:
        '''
        return the control identifiers as a string.
        by default, print_control_identifiers prints to stdout.
        '''
        # Create a StringIO object to capture the output
        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output

        if isinstance(o, UIAWrapper):
            w = self.get_windowspec_from_uiawrapper(o)
        else:
            w = o

        try:
            # Call print_control_identifiers()
            w.print_control_identifiers()
        finally:
            # Restore standard output
            sys.stdout = old_stdout

        # Get the captured output as a string
        control_identifiers_string = redirected_output.getvalue()

        return control_identifiers_string

    # def get_prompt(self) -> str:
    #     prompt = ""
    #     for k in sorted(self.usage.keys()):
    #         v = self.usage[k]
    #         short = v.get('short', k)
    #         prompt += f"{short}-{k} "
    #     return prompt


    def refresh_window_specs(self, **opt):
        debug = opt.get('debug', False)

        top_window_child_specs = self.get_child_specs(self.top_window, debug=debug)
        self.window_and_child_specs = []  # list of (window, which, child_spec)
        for s in top_window_child_specs:
            self.window_and_child_specs.append( (self.top_window, 'top_window', s) )

        if self.current_window and self.current_window != self.top_window:
            current_window_child_specs = []
            try:
                current_window_child_specs = self.get_child_specs(self.current_window, debug=debug)
            except pywinauto.findwindows.ElementNotFoundError as e:
                print(f"ElementNotFoundError: current_window is not valid, either closed or you need to wait longer.")
                return
            
            for s in current_window_child_specs:
                self.window_and_child_specs.append( (self.current_window, 'current_window', s) )

    def locate(self, long_cmd: str, arg: str, ret0: dict, **opt):
        debug = opt.get('debug', False)
        verbose = opt.get('verbose', 0)
        
        ret = ret0.copy()

        if long_cmd == 'child':
            idx = int(arg)
            max_child_specs = len(self.window_and_child_specs)
            if idx < 0 or idx >= max_child_specs:
                print(f"invalid idx {idx}, must be between 0 and {max_child_specs-1}")
                ret['bad_input'] = True
            else:
                w, which, child_spec = self.window_and_child_specs[idx]
                print(f"exploring child {idx}: {child_spec} from {which}")
                # extract args from child_window(...)

                code = f"self.{which}.{child_spec}"
                print(f"code={code}")
                self.current_window = eval(code, globals(), locals())
                # w2 = w.child_window( control_type="Document")
                
                try: 
                    self.current_window.click_input()
                    sleep(1)
                except pywinauto.timings.TimeoutError as e:
                    print(f"TimeoutError: child spec didn't appear in time.")
                    self.current_window = None
                except pywinauto.findwindows.ElementNotFoundError as e:
                    print(f"ElementNotFoundError: child spec is not valid, either closed or you need to wait longer.")
                    self.current_window = None

                if self.current_window is not None:
                    # after a successful click, we refresh our control identifiers tree.
                    self.refresh_window_specs()
                    ret['relist'] = True
        elif long_cmd == "connect":
            if arg.startswith("title_re="):
                title_re = arg[len("title_re="):]
                self.app.connect(title_re=title_re)
                self.top_window = self.app.top_window()
                self.current_window = self.top_window
                self.top_window.wait('visible')
                self.top_window.click_input()  # ensure the window is focused
                sleep(1)
                print(f"connected to window with title_re={title_re}")
            else:
                raise ValueError(f"invalid connect arg {arg}, must start with title_re=")
        elif long_cmd == 'control_identifiers':
            if self.current_window is None:
                print("current_window is None, cannot get control identifiers")
                ret['bad_input'] = True
            else:
                try:
                    ci_string = self.get_control_identifiers(self.current_window)
                    print(f"current_window control identifiers:\n{ci_string}")
                except pywinauto.findwindows.ElementNotFoundError as e:
                    print(f"ElementNotFoundError: current_window is not valid, either closed or you need to wait longer.")
                    ret['bad_input'] = True
        elif long_cmd == 'start':
            self.app.start(arg)
            sleep(2) # wait for the app to start
                    
            '''
            app.start("notepad.exe") 
            app.top_window()
            error:
                    in top_window
                    raise RuntimeError("No windows for that process could be found")

            likely due to notepad spawning a new process for the window. 
            therefore, if we try-catch this error, then we can use app.connect to connect to the window.
            '''
        
            try:
                self.top_window = self.app.top_window()
            except RuntimeError as e:
                print(f"RuntimeError: {e}")
                # if the error is "No windows for that process could be found"
                if "No windows for that process could be found" in str(e):
                    print(f"seeing error 'No windows for that process could be found', likely due to app spawning a new process for the window.")
                    print(f"we will try to connect to the window with title_re=\"{self.title_re}\"")

            if self.top_window is not None:
                self.current_window = self.top_window
                self.top_window.wait('visible')
                self.top_window.click_input()  # ensure the window is focused
                sleep(1)
        elif long_cmd == 'text':
            if self.current_window is None:
                print("current_window is None, cannot get text")
                ret['bad_input'] = True
            else:
                try:
                    texts = self.current_window.texts()
                    print(f"current_window texts={texts}")
                except pywinauto.findwindows.ElementNotFoundError as e:
                    print(f"ElementNotFoundError: current_window is not valid, either closed or you need to wait longer.")
                    ret['bad_input'] = True
        elif long_cmd == 'top':
            self.title_recurrent_window = self.top_window
            print("current_window is now top_window")
        elif long_cmd == 'type':
            # replace \n with {ENTER}
            arg = arg.replace('\n', '{ENTER}')
            self.current_window.type_keys(arg, with_spaces=True, pause=0.05)
        else:
            print(f"invalid long_cmd {long_cmd}")
            ret['bad_input'] = True
        
        return ret


    def get_child_specs(self, w: WindowSpecification, **opts) -> list[str]:
        '''
        return the list of child specs as strings.
        each child spec is like: child_window(title="Maximize", control_type="Button")
        '''

        debug = opts.get('debug', False)
        ci_string = self.get_control_identifiers(w)
        children = []
        multiline = ci_string
        # extract line like: child_window(title="\rhello\rworld\r", control_type="Document")
        # note this is a multi-line match because title can contain \r which is a line break.

        #    |    | child_window(title="Maximize", control_type="Button")
        while m := re.match(r".*?(child_window\(.+?\))", multiline, re.MULTILINE|re.DOTALL):
            child_spec = m.groups()[0]
            multiline = multiline[m.end():] # leftover string to be processed

            '''
            example of child_spec:
                child_window(title="\rcurrent time=2025-08-23 02:40:46\r9:40 PM 8/22/2025", control_type="Document")
            challenges:
                - the child_spec's title can contain \r which is a line break.
                    we should pick a substring of title that doesn't contain \r.
                - there can be escaped quotes in the title.
                - also we should reduce the length of title to at most 30 characters.
            '''
            title_match = re.search(r'title="((?:[^"\\]|\\.)*)"', child_spec, re.DOTALL)
            if title_match:
                full_title = title_match.groups()[0]
                debug and print(f"full_title={full_title}")
                short_titles = re.split(r'\t|\n|\r|\{|\}|\]|\[|\\r', full_title)
                debug and print(f"short_titles={short_titles}")

                # if short_titles length is 1, it means no \r in title.
                # if short_titles length > 1, it means there are \r in title.
                # in that case, we should pick the longest substring.
                if len(short_titles) > 1:
                    debug and print(f"full_title={full_title}, short_titles={short_titles}")
                    
                    # method1. 
                    # pick the longest substring
                    longest_short_title = max(short_titles, key=len)
                    debug and print(f"longest_short_title={longest_short_title}")
                    
                    longest_short_title = longest_short_title[:30] # truncate to at most 30 characters
                    
                    # replace the title part in child_spec
                    child_spec = child_spec.replace(f'title="{full_title}"', f'title_re=".*{longest_short_title}.*"')

                    # method 2.
                    # child_spec = child_spec.replace(f'title="{full_title}",','') # remove title part entirely
            children.append(child_spec)
        return children
    
    def display_f(self):
        i = 0
        for w, which, s in self.window_and_child_specs:
            print(f"{i}: {which}.{s}")
            i += 1

    # for exploretools.Explorer
    locate_f = locate
    refresh_states_f = refresh_window_specs
    usage_by_long = usage

def explore(**opt):
    pwa = PwaEnv(**opt)
    
    for step in pwa.init_steps:
        long_cmd, arg, *_ = step.split('=', 1) + [None]
        print(f"init step: {long_cmd}={arg}")
        pwa.locate(long_cmd, arg, {}, **opt)
    pwa.refresh_window_specs(**opt)

    explorer = tpsup.exploretools.Explorer(
        locate_f=pwa.locate,
        display_f=pwa.display_f,
        refresh_states_f=pwa.refresh_window_specs,
        app_usage_by_long=pwa.usage,
        **opt
    )
    explorer.explore(**opt)
