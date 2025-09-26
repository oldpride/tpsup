import io
from pprint import pformat
import re
import sys
from time import sleep
import pywinauto
from pywinauto.application import Application, WindowSpecification
from pywinauto.controls.uiawrapper import UIAWrapper
from tpsup.cmdtools import run_cmd

from typing import Union
import tpsup.locatetools
from tpsup.logbasic import log_FileFuncLine

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


class UiaEnv:
    locate: callable = None
    follow: callable = None
    explore: callable = None

    search_action: str = 'print' # print, click, type=...  default is print
    search_title_re: str = None
    search_type: str = 'any' # search control_type: any, Window, Button, Edit, etc.

    def __init__(self, 
                 **opt):
        
        self.app: Application = opt.get('app', None)
        self.desktop = opt.get('desktop', None)
        self.title_re: str = opt.get('title_re', None)
        self.title: str = opt.get('title', None)
        self.window_and_child_specs = []
        self.current_window: WindowSpecification = None # a sub-window of the top_window
        self.top_window: WindowSpecification = None # top window of the connected app

        # self.init_steps = opt.get('init_steps', [])
        
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

        if not self.desktop:
            self.desktop = pywinauto.Desktop(backend=self.backend)
        
        locateEnv = tpsup.locatetools.LocateEnv(
            locate_cmd_arg=self.locate_cmd_arg,
            locate_dict=self.locate_dict,
            locate_usage_by_cmd=self.locate_usage_by_cmd,
            display=self.display,
            **opt)
        self.locate = locateEnv.locate
        self.follow = locateEnv.follow
        self.explore = locateEnv.explore

    locate_usage_by_cmd = {
        'children': {
            'short': 'ch',
            'no_arg': True,
            'usage': '''
                list all child windows of the current window.
                ch
            ''',
        },
        'connect': {
            'short': 'conn',
            'need_arg': True,
            'has_dryrun': True,
            'usage': '''
                connect with title_re, title
                conn=title_re=.*tianjunk.*
                conn=title="tianjunk - Notepad"
                ''',
        },
        'child': {
            'short': 'c',
            'need_arg': True,
            'usage': '''
                click the child window by index.
                examples:
                c=13
                ''',
        },
        'click': {
            'short': 'cl',
            'no_arg': True,
            'usage': '''
                click the the current window.
                examples:
                click
                ''',
        },
        'control_identifiers': {
            'short': 'ci',
            'no_arg': True,
            'usage': '''
                get the control identifiers of the current window
                ci
            ''',
        },
        'desktop': {
            'short': 'desk',
            'usage': '''
                list all top windows of the desktop.
                'connect' command can be used to connect to one of the top windows.
                examples:
                    desk         # list all top windows of the desktop
                    desk=notepad # list all top windows of the desktop whose title contains 'notepad'
            ''',
        },
        'list': {
            'short': 'l',
            'no_arg': True,
            'usage': '''
                list the child windows of the top window and current window
                l
            ''',
        },
        'refresh': {
            'no_arg': True,
            'usage': '''
                refresh the child window list
                r
            ''',
        },
        'search': {
            'need_arg': True,
            'has_dryrun': 1,
            'usage': '''
                search=scope

                search for windows matching the criteria.
                (similar to unix 'find' command)

                scope can be:
                    desktop  - search all desktop windows
                    top      - search only the top window of the connected app
                    current  - search only the current window of the connected app

                examples:
                    search=desktop
                    search=top
                    search=current

                see also:
                    search_act
                    search_title_re
                    search_type
            ''',
        },
        'search_act': {
            'short': 'sa',
            'usage': '''
                set action for search results.
                default is 'print'.
                without arg, we print the current action.
                examples:
                    act      # print current action
                    act=print  # set action to print
                    act=click  # set action to click
                    act=type=Y{ENTER}
            ''',
        },
        'search_title_re': {
            'short': 'str',
            'usage': '''
                set search title_re for search results.
                default is None.
                without arg, we print the current title_re.
                examples:
                    search_title_re      # print current title_re
                    search_title_re=.*   # set title_re to .*
                    search_title_re=.*notepad.*  # set title_re to .*notepad.*
            ''',
        },
        'search_type': {
            'short': 'sty',
            'usage': '''
                set search control_type for search results.
                default is 'any'.
                without arg, we print the current control_type.
                examples:
                    search_type      # print current control_type
                    search_type=any  # set control_type to any
                    search_type=Window  # set control_type to Window
                    search_type=Button  # set control_type to Button
            ''',
        },
        'start': {
            'need_arg': True,
            'usage': '''
                start=notepad.exe
                start="C:\\Program Files\\Mozilla Firefox\\firefox.exe"
                start="C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
                s="C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
                ''',
        },
        'texts': {
            'usage': '''
                get the texts of the current window.
                if variable is given, store the texts in the list, a global var.
                texts
                texts=varname
            examples:
                texts
                texts=txt_list                
            ''',
        },
        'title': {
            'siblings': ['title_re'],
            'usage': '''
                set or get title or title_re.
                    - set: set the title or title_re for the next 'start' command.
                    - get: get the current value of title or title_re.
                    - unset: set title or title_re to None
                note: 'connect' has a arg for title or title_re, different from this command.
                examples:
                    title="notepad - Notepad"
                    title_re=.*notepad.*
                    title
                    title_re
                    title=unset
                    title_re=unset

            ''',
        },
        'top' : {
            'no_arg': True,
            'usage': '''
                get the top window of the connected application.
                top

                note: 
                    - only pywinauto.Application has top_window().
                    - pywinauto.Desktop doesn't have top_window().
                    - desktop has top windows which we can connect to.
            ''',
        },
        'type': {
            'short': 'ty',
            'need_arg': 1,
            'usage': '''
                ty=hello
                ty="hello world"
                ty={UP}
                ty={ENTER}
                ty={F5}
            ''',
        },
    }

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

    # def recursive_child(self, w: WindowSpecification, 
    #                     action_list: list[dict] = [],
    #                     depth=0, max_depth=5, **opt) -> list[str]:
    #     '''
    #     recursively get child specs up to max_depth, without clicking it, because 
    #     clicking may have side effects.

    #     action_list is a list of dict,
    #         {
    #             'control_type': 'Button', # or 'Window', default to None meaning any type
    #             'title_re': 'please', # default to None meaning any title
    #             'action': 'click' # or 'print', default to 'print' the child spec
    #         }
    #     '''

    #     debug = opt.get('debug', False)
        
    #     if depth > max_depth:
    #         return []

    #     # Get the child specs
    #     child_specs = self.get_child_specs(w, debug=debug)

    #     for cs in child_specs:
    #         # Check if the child spec matches the action list
    #         for action in action_list:
    #             if 'title_re' in action:
    #                 title_re = action['title_re']
    #                 title = w.child_window(**cs).window_text()
    #                 if not re.search(title_re, title, re.I):
    #                     continue
    #             if 'control_type' in action:
    #                 expected_ct = action['control_type'].lower()
    #                 if expected_ct != 'any' and expected_ct != cs.get('control_type', '').lower():
    #                     continue
    #             act = action.get('action', 'print')
    #             if act == 'print':
    #                 print(f"child spec: {cs}")
    #             elif act == 'click':
    #                 self.click_window(cs, **opt)
    #         # Recursively get the child specs
    #         self.recursive_child(cs, action_list=action_list, depth=depth+1, max_depth=max_depth, **opt)

    #     return []

    def search_process_window(self, w: WindowSpecification, **opt) -> bool:
        '''
        process a window in search mode, according to 
        - control_type
        - title_re
        '''
        debug = opt.get('debug', False)
        title = w.window_text()
        ct = w.element_info.control_type
        if self.search_title_re is not None:
            if not re.search(self.search_title_re, title, re.IGNORECASE):
                return False
            elif debug:
                print(f"matched title_re {self.search_title_re} with title {title}")
        if not self.search_type:
            if self.search_type.lower() == 'any' or self.search_type.lower() == ct.lower():
                print(f"matched control_type {self.search_type} with control_type {ct}")
            elif debug:
                print(f"control_type {ct} doesn't match {self.search_type}")
                return False

        # if we reach here, we have a match
        if not self.search_action or self.search_action.lower() == 'print':
            print(f"search matched window: {w}, title={title}, control_type={ct}")
        elif self.search_action.lower() == 'click':
            self.click_window(w, **opt)
        elif self.search_action.lower().startswith('type='):
            to_type = self.search_action[5:]
            print(f"typing '{to_type}' into window: {w}, title={title}, control_type={ct}")
            w.type_keys(to_type, with_spaces=True, set_foreground=True)
            sleep(1)
        else:
            print(f"unknown search action {self.search_action}")
            raise ValueError(f"unknown search action {self.search_action}")
    def click_window(self, w: WindowSpecification, **opt) -> bool:
        try:
            w.click_input()
            sleep(1)
        except pywinauto.timings.TimeoutError as e:
            print(f"TimeoutError: child spec didn't appear in time.")
            return False
        except pywinauto.findwindows.ElementNotFoundError as e:
            print(f"ElementNotFoundError: child spec is not valid, either closed or you need to wait longer.")
            return False
        return True

    def locate_cmd_arg(self, long_cmd: str, arg: str, **opt):
        debug = opt.get('debug', False)
        verbose = opt.get('verbose', 0)
        dryrun = opt.get('dryrun', False)
        
        ret = tpsup.locatetools.ret0.copy()

        if long_cmd == 'children':
            if self.current_window is None:
                print("current_window is None, cannot list children")
                ret['bad_input'] = True
            else:
                for descendant_window in self.current_window.descendants():
                    print(f"desc window={pformat(descendant_window)}, "
                          f"title={descendant_window.window_text()}, "
                          f"control_type={descendant_window.element_info.control_type}, "
                          f"python={type(descendant_window).__name__}, "
                          f"class_name={descendant_window.class_name()}")
                    # print(f"dir(descendant_window)={dir(descendant_window)}")
                    # print(f"element_info={pformat(descendant_window.element_info)}")
                    # print(f"dir(element_info)={dir(descendant_window.element_info)}")
        elif long_cmd == 'child':
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
                
                # if not self.click_window(self.current_window, **opt):
                #     self.current_window = None

                # if self.current_window is not None:
                #     # after a successful click, we refresh our control identifiers tree.
                #     self.refresh_window_specs()
                #     ret['relist'] = True
                result = self.locate_cmd_arg('click', '', **opt)
                ret.update(result)
        elif long_cmd == 'click':
            if self.current_window is None:
                print("current_window is None, cannot click")
                ret['bad_input'] = True
            else:
                if not self.click_window(self.current_window, **opt):
                    self.current_window = None

                if self.current_window is not None:
                    # after a successful click, we refresh our control identifiers tree.
                    self.refresh_window_specs()
                    ret['relist'] = True
        elif long_cmd == "connect":
            '''
            connect with title_re, title
            connect=title_re=.*tianjunk.*
            connect=title="tianjunk - Notepad"
            '''
            k,v = arg.split('=', 1)
            if k == 'title_re' or k == 'title':
                print(f"connecting to window with {k}={v}")

                # remove quotes if any
                if (v.startswith('"') and v.endswith('"')) or \
                   (v.startswith("'") and v.endswith("'")):
                    v = v[1:-1]
                elif (v.startswith('"') and not v.endswith('"')) or \
                     (v.startswith("'") and not v.endswith("'")):
                    raise ValueError(f"unmatched quote in {k}={v}")

                if dryrun:
                    return ret
                
                if k == 'title_re':
                    result = self.app.connect(title_re=v)
                else:
                    result = self.app.connect(title=v)
                print(f"after connected, result={result}")
                self.top_window = self.app.top_window()
                self.current_window = self.top_window
                self.top_window.wait('visible')
                self.top_window.click_input()  # ensure the window is focused
                sleep(1)
                print(f"connected to window with {k}={v}, top_window={self.top_window}")
                self.refresh_window_specs()
            else:
                raise ValueError(f"invalid connect arg {arg}, must start with title_re= or title=")
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
        elif long_cmd == 'desktop':
            '''
            list all top windows of the desktop.
            'connect' command can be used to connect to one of the top windows.
            examples:
                desk         # list all top windows of the desktop
                desk=notepad # list all top windows of the desktop whose title contains 'notepad'
            '''
            title_filter = arg if arg else None
            print(f"listing all top windows of the desktop, title_filter={title_filter}")
            top_windows: list[pywinauto.WindowSpecification] = self.desktop.windows()
            for w in top_windows:
                title = w.window_text()
                if title_filter is None or re.search(title_filter, title, re.IGNORECASE):
                    print(f"desktop top window, conn=title={title}")
        elif long_cmd == 'list':
            self.display()
        elif long_cmd == 'refresh':
            self.refresh_window_specs()
        elif long_cmd == 'search':
            '''
            search=scope
            '''
            scope = arg

            if scope == 'desktop':
                # start searching from desktop windows
                desktop_top_windows = self.desktop.windows()
                for tw in desktop_top_windows:
                    # drill into each top window
                    for descendant_window in tw.descendants():
                        if debug:
                            print(f"descendant_window={pformat(descendant_window)}, "
                                f"title={descendant_window.window_text()}, "
                                f"control_type={descendant_window.element_info.control_type}, "
                                f"python={type(descendant_window).__name__}, "
                                f"class_name={descendant_window.class_name()}")
                            self.search_process_window(descendant_window)
            elif scope == 'top':
                if self.top_window is None:
                    print("top_window is None, cannot search")
                    ret['bad_input'] = True
                else:
                    for descendant_window in self.top_window.descendants():
                        if debug:
                            print(f"descendant_window={pformat(descendant_window)}, "
                                f"title={descendant_window.window_text()}, "
                                f"control_type={descendant_window.element_info.control_type}, "
                                f"python={type(descendant_window).__name__}, "
                                f"class_name={descendant_window.class_name()}")
                        self.search_process_window(descendant_window)
            elif scope == 'current':
                if self.current_window is None:
                    print("current_window is None, cannot search")
                    ret['bad_input'] = True
                else:
                    for descendant_window in self.current_window.descendants():
                        if debug:
                            print(f"descendant_window={pformat(descendant_window)}, "
                                f"title={descendant_window.window_text()}, "
                                f"control_type={descendant_window.element_info.control_type}, "
                                f"python={type(descendant_window).__name__}, "
                                f"class_name={descendant_window.class_name()}")
                        self.search_process_window(descendant_window)
            else:
                print(f"invalid search scope {scope}, must be one of desktop, top, current")
                ret['bad_input'] = True

        elif long_cmd == 'search_act':
            '''
            set action for search results.
            default is 'print'.
            without arg, we print the current action.
            examples:
                act      # print current action
                act=print  # set action to print
                act=click  # set action to click
                act=type=Y{ENTER}
            '''
            if not arg:
                print(f"current action = {self.search_action}")
            elif arg == 'unset':
                self.search_action = None
                print(f"unset action")
            else:
                self.search_action = arg
                print(f"set action = {self.search_action}")
        elif long_cmd == 'search_title_re':
            '''
            set search title_re for search results.
            default is None.
            without arg, we print the current title_re.
            examples:
                search_title_re      # print current title_re
                search_title_re=.*   # set title_re to .*
                search_title_re=.*notepad.*  # set title_re to .*notepad.*
            '''
            if not arg:
                print(f"current search_title_re = {self.search_title_re}")
            elif arg == 'unset':
                self.search_title_re = None
                print(f"unset search_title_re")
            else:
                self.search_title_re = arg
                print(f"set search_title_re = {self.search_title_re}")
        elif long_cmd == 'search_type':
            '''
            set search control_type for search results.
            default is 'any'.
            without arg, we print the current control_type.
            examples:
                search_type      # print current control_type
                search_type=any  # set control_type to any
                search_type=Window  # set control_type to Window
                search_type=Button  # set control_type to Button
            '''
            if not arg:
                print(f"current search_type = {self.search_type}")
            elif arg == 'unset':
                self.search_type = 'any'
                print(f"unset search_type, set to default 'any'")
            elif arg.lower() in ['any', 'window', 'button']:
                self.search_type = arg.lower()
                print(f"set search_type = {self.search_type}")
            else:
                print(f"invalid search_type {arg}, must be one of any, Window, Button")
                ret['bad_input'] = True
        elif long_cmd == 'start':
            '''
            when the start command spawns a new process for the window,
            app.top_window() may not work because it only works for the original process.
            we will have to connect to the window with title_re or title.
            but if title is not unique, we may connect to the wrong window.
            to mimimize this error, we try to connect to the new top window of the 
            desktop (note: desktop vs app).
            to find out the new window, we need to save the list of top windows
            before and after the start command.
            '''

            # save the list of top windows of the desktop before starting the app
            desktop_top_windows_before: list[pywinauto.WindowSpecification] = self.desktop.windows()
            self.app.start(arg)
            sleep(2) # wait for the app to start

            # save the list of top windows of the desktop after starting the app
            desktop_top_windows_after: list[pywinauto.WindowSpecification] = self.desktop.windows()
            '''
            app.start("notepad.exe") 
            app.top_window()
            error:
                    in top_window
                    raise RuntimeError("No windows for that process could be found")

            likely due to notepad spawning a new process for the window. 
            therefore, if we try-catch this error, then we can use the following ways to
            connect to the window:
                1. use Desktop.windows() to find the new top window of the desktop
                2. use app.connect() to connect by title_re or title if given.
            '''

            # reset top_window and current_window before calling 'start'
            self.top_window = None
            self.current_window = None

            try:
                self.top_window = self.app.top_window()
            except RuntimeError as e:
                print(f"RuntimeError: {e}")
                # if the error is "No windows for that process could be found"
                if "No windows for that process could be found" in str(e):
                    print(f"seeing error 'No windows for that process could be found', likely due to app spawning a new process for the window.")
                    print(f"we will search for it in new windows of the desktop.")

            if self.top_window :
                print(f"after start, top_window={self.top_window}")
                self.current_window = self.top_window
                self.top_window.wait('visible')
                self.top_window.click_input()  # ensure the window is focused
                sleep(1)
                self.refresh_window_specs()
            else:
                print(f"search for the new top window of the desktop.")
                # app.start() lost track of the child process.
                # we try to find the new top window of the desktop
                new_top_windows = []
                for w_after in desktop_top_windows_after:
                    if not any(w_after.handle == w_before.handle for w_before in desktop_top_windows_before):
                        new_top_windows.append(w_after)
                if len(new_top_windows) == 0:
                    print(f"no new top window found after running start command.")

                    # we don't set failure here, because we may run 'connect' later to connect to the window.
                    # ret['success'] = False
                    return ret
                print(f"new top windows found after running start command:")
                for w in new_top_windows:
                    print(f"    {w}, title={w.window_text()}, {pformat(w)}")

                # filter new_top_windows with different criteria
                if self.title:
                    filtered_windows = [w for w in new_top_windows if w.window_text() == self.title]
                    if not filtered_windows:
                        print(f"no new top window found after running start command with title={self.title}")
                        return ret
                    else:
                        new_top_windows = filtered_windows 
                        # narrow down to filtered windows, prepare for next filter

                if self.title_re:
                    filtered_windows = [w for w in new_top_windows if re.search(self.title_re, w.window_text(), re.IGNORECASE)]
                    if not filtered_windows:
                        print(f"no new top window found after running start command with title_re={self.title_re}")
                        return ret
                    else:
                        new_top_windows = filtered_windows
                        # narrow down to filtered windows, prepare for next filter

                if len(new_top_windows) > 1:
                    print(f"multiple new top windows found after running start command, please refine title or title_re to narrow down:")
                    for w in new_top_windows:
                        print(f"    {w}, title={w.window_text()}")
                    return ret
                    
                self.current_window = self.top_window

                # AttributeError: 'UIAWrapper' object has no attribute 'wait'
                # self.top_window.wait('visible')
                if isinstance(self.top_window, UIAWrapper):
                    self.top_window = self.get_windowspec_from_uiawrapper(self.top_window)
                self.top_window.wait('visible')
                
                self.top_window.click_input()  # ensure the window is focused
                sleep(1)
                self.refresh_window_specs()
        elif long_cmd == 'texts':
            '''
            texts
            texts=list_var
            '''
            # get the texts of the current window
            if self.current_window is None:
                print("current_window is None, cannot get texts") 
            else:
                try:
                    texts = self.current_window.texts()
                    print(f"current_window texts={texts}")

                    if arg:
                        print(f"cannot store texts (list) to global variable {arg}")
                        # store the texts in the global variable
                        globals()[arg] = texts
                except pywinauto.findwindows.ElementNotFoundError as e:
                    print(f"ElementNotFoundError: current_window is not valid, either closed or you need to wait longer.")
                    ret['bad_input'] = True
        elif long_cmd == 'title' or long_cmd == 'title_re':
            '''
            title="notepad - Notepad"
            title_re=.*notepad.*
            title
            title_re
            title=unset
            title_re=unset
            '''
            if not arg:
                # get title or title_re
                if long_cmd == 'title':
                    print(f"self.title={self.title}")
                else:
                    print(f"self.title_re={self.title_re}")
            if arg:
                # set title or title_re
                v = arg
                # remove quotes if any
                if (v.startswith('"') and v.endswith('"')) or \
                   (v.startswith("'") and v.endswith("'")):
                    v = v[1:-1]
                elif (v.startswith('"') and not v.endswith('"')) or \
                     (v.startswith("'") and not v.endswith("'")):
                    raise ValueError(f"unmatched quote in {long_cmd}={v}")
                
                if v == 'unset':
                    v = None

                if long_cmd == 'title':
                    self.title = v
                    print(f"set title to {self.title}")
                else:
                    self.title_re = v
                    print(f"set title_re to {self.title_re}")
        elif long_cmd == 'top':
            '''
            top
            '''
            if self.top_window is None:
                print("top_window is None, cannot get top window. Did you start or connect to an app?")
                ret['bad_input'] = True
            else:
                print("current_window is now top_window")
                self.current_window = self.top_window
                self.refresh_window_specs()
        elif long_cmd == 'type':
            # replace \n with {ENTER}
            arg = arg.replace('\n', '{ENTER}')
            self.current_window.type_keys(arg, with_spaces=True, pause=0.05)
        else:
            print(f"invalid long_cmd {long_cmd}")
            ret['bad_input'] = True
        
        return ret

    def locate_dict(self, locator: dict, **opt) -> dict:
        ret = tpsup.locatetools.ret0.copy()
        print("locate_ditct() is not implemented yet")
        return ret
        
    def get_child_specs(self, w: WindowSpecification, **opts) -> list[str]:
        '''
        return the list of child specs as strings.
        each child spec is like: child_window(title="Maximize", control_type="Button")
        '''

        debug = opts.get('debug', False)
        use_original_spec = opts.get('use_original_spec', False)

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

            if use_original_spec:
                children.append(child_spec)
                continue

            # now use_original_spec is False
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
    
    def display(self):
        i = 0
        for w, which, s in self.window_and_child_specs:
            print(f"{i}: {which}.{s}")
            i += 1

# the following is for batch framework - batch.py
#
# pre_batch and post_batch are used to by batch.py to do some setup and cleanup work
# '
# known' is only available in post_batch, not in pre_batch.

def pre_batch(all_cfg, known, **opt):
    # init global variables.
    # UiaEnv class doesn't need global vars because it is Object-Oriented
    # but batch.py uses global vars to shorten code which will be eval()/exec()
    global driverEnv

    log_FileFuncLine(f"running pre_batch()")
    if all_cfg["resources"]["uia"].get('driverEnv', None) is None:
        # driverEnv is created in delayed mode
        method = all_cfg["resources"]["uia"]["driver_call"]['method']
        kwargs = all_cfg["resources"]["uia"]["driver_call"]["kwargs"]
        # driverEnv = method(**kwargs)
        driverEnv = method(**{**kwargs, **opt})
        # 'host_port' are in **opt
        all_cfg["resources"]["uia"]['driverEnv'] = driverEnv
        log_FileFuncLine(f"driverEnv is created in batch.py's delayed mode")

def post_batch(all_cfg, known, **opt):
    dryrun = opt.get('dryrun', False)
    print("")
    print("--------------------------------")

    if dryrun:
        print("dryrun, skip post_batch()")
        return
    
    print(f"running post_batch()")

    driverEnv = None
    try: 
        driverEnv = all_cfg["resources"]["uia"]["driverEnv"]
    except Exception as e:
        print(f"driverEnv is not created, skip cleanup")
        return
 

    # log_FileFuncLine(f"kill chromedriver if it is still running")
    # tpsup.pstools.kill_procs(procs, **opt)

tpbatch = {
    'pre_batch': pre_batch,
    'post_batch': post_batch,
    "extra_args": {
        'humanlike': {
            "switches": ["--humanlike"],
            "default": False,
            "action": "store_true",
            "help": "add some random delay to make it more humanlike",
        },
        'explore': {
            'switches': ['-explore', '--explore'],
            'action': 'store_true',
            'default': False,
            'help': "enter explore mode at the end of the steps"
        },
    },  
    "resources": {
        "uia": {
            "method": UiaEnv,
            # "cfg": {},

            "init_resource": 0,  # delay init until first use. this logic is in batch.py
        },
    },
}


def main():
    pass

if __name__ == "__main__":
    main()
