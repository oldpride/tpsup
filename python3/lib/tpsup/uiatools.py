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
import tpsup.keyvaluetools
import threading

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
                print(f"{k}'s window_text={clean_text(x.window_text())}")
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
            print(f"{k}'s child window={w}, title={clean_text(w.window_text())}, python={type(w).__name__}, class_name={w.class_name()}")

class UiaEnv:
    locate: callable = None
    follow: callable = None
    explore: callable = None

    descendants: list = []  # list of dict with keys: window, title, control_type, class_name 
                            # of the current top window.

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
        
        self.backend = 'uia'

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
        'backend': {
            'usage': '''
                get or set the backend to win32 or uia. default is uia.
                examples:
                backend     # get the current backend
                backend=uia
                backend=win32

                changing backend 
                - change 'app' and 'desktop' to use the new backend.
                - will not trigger re-connect, use 'connect' command to re-connect.
            ''',
        },
        'descendants': {
            'short': 'desc',
            'has_dryrun': 1,
            'usage': '''
                list all descendant windows of the current window. 
                showing parent-child relationship using indentation.
                some children will only show after you click parent.
                attributes:
                    depth:     max depth of children, default 5
                    count:     max number of descendants to list, default 100
                    timeout:      default 2s
                example:
                    desktop
                    conn=title="Program Manager"

                    desc             # default depth=5
                    desc=depth=1     # only the children of top window
                    desc=timeout=2
                to list descendants of top window, use 'top' command to switch 
                    current window to top window first.
            ''',
        },
        'child': {
            'short': 'c',
            'need_arg': True,
            'usage': '''
                child=index
                child=spec
                locate a child index from the descendants list or a spec.
                this makes the located child the current window, but not click it.
                examples:
                    c=13
                    c=title="Untitled - Notepad" control_type="Edit"
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
        'connect': {
            'short': 'conn',
            'need_arg': True,
            'has_dryrun': True,
            'usage': '''
                connect with title_re, title
                examples:
                conn=title_re=.*tianjunk.* 
                conn=title="tianjunk - Notepad"
                conn=title_re=.*/Users/tian # for cygwin mintty
                ''',
        },
        'current': {
            'no_arg': True,
            'usage': '''
                print the current window spec.
                current
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
        'find': {
            'need_arg': True,
            'has_dryrun': 1,
            'usage': '''
                search for windows matching the criteria.
                similar to unix 'find' command.
                    find=criterias

                criterias are key=value pairs separated by space.
                    action=<action>
                    class=<class_name>
                    scope=<scope> 
                    title=<title>
                    title_re=<title_re>  
                    type=<control_type>
                    pid=<process_id>
                    auto_id=<automation_id>

                    # search setting
                    timeout=<seconds>
            
                2nd level criterias
                    scope2=<scope2>
                    title2=<title2>
                    title_re2=<title_re2>
                    type2=<control_type2>
                    class2=<class_name2>
                    auto_id2=<automation_id2>
                2nd level criteria is needed when, 
                    for example, we want to close a error popup.
                        find=title="Close" control_type="Button"
                    but this critera is too broad, because there may be many buttons with title="Close".
                    therefore, we need to narrow down with
                        find=title_re=".*Connection timed out.*" scope=desktop title2="Close" type2="Button"

                'action' will act on level 2 matched windows if level 2 criteria is given;
                otherwise, 'action' will act on level 1 matched windows.

                scope can be:
                    desktop  - search all desktop windows
                    top      - search only the top window and its children of the connected app, this is the default scope.
                    current  - search only the current window and its children of the connected app
                scope2 can be:
                    child - search the child windows of the matched level 1 windows.
                            somehow I always got empty list.
                    all   - search the matched level 1 windows' top-window's descendants.
                            basically adding siblings, uncles, cousins, etc, in addition to children.
                            this is the default.

                timeout
                    the maximum time to search for each top-level window.
                    default is 5 seconds.

                title_re/title2 can be:
                    .*      - match any title
                    notepad - match title containing 'notepad'

                title/title2 
                    the exact title to match.

                type/type2
                    is the control_type to match, eg, Window, Button, Edit, Text, etc.

                class/class2
                    the class_name to match, eg, Notepad, Edit, etc.

                action can be:
                    print   - print the find results
                    click   - click the find results
                    type    - type text into the find results

                examples:
                    find=title_re=.*tianjunk.* type=any action=print
                    find=scope=desktop title_re=.*notepad.* type=Window action=print
                    find=scope=top title_re=.*notepad.* type=Button action=click
                    find=scope=current title_re=.*notepad.* type=Edit action=type=hello{ENTER}
                    find=title_re=".*Connection timed out.*" scope=desktop # find putty error dialog
                    find=title_re=".*Connection timed out.*" scope=desktop title2="Close" type2="Button"
                    find=title_re=".*Connection timed out.*" scope=desktop title2="Close" type2="Button" action=click

                if search scope was desktop, you can use 'connect=title=...' to connect to the matched top window.
                
            ''',
        },        
        'list': {
            'short': 'li',
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
            'usage': '''
                top           # switch current window to top window.
                top=<index>   # switch current window to the top window by index from 'desktop' command.

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



    # def refresh_window_specs(self, **opt):
    #     debug = opt.get('debug', False)

    #     top_window_child_specs = self.get_child_specs(self.top_window, debug=debug)
    #     self.window_and_child_specs = []  # list of (window, which, child_spec)
    #     for s in top_window_child_specs:
    #         self.window_and_child_specs.append( (self.top_window, 'top_window', s) )

    #     if self.current_window and self.current_window != self.top_window:
    #         current_window_child_specs = []
    #         try:
    #             current_window_child_specs = self.get_child_specs(self.current_window, debug=debug)
    #         except pywinauto.findwindows.ElementNotFoundError as e:
    #             print(f"ElementNotFoundError: current_window is not valid, either closed or you need to wait longer.")
    #             return
            
    #         for s in current_window_child_specs:
    #             self.window_and_child_specs.append( (self.current_window, 'current_window', s) )


    def find_process_one_window(self, w1: WindowSpecification, 
                              mc1: dict, # match criteria
                              search_top_window: WindowSpecification,
                              level2_dict: dict, # level 2 match criteria
                              **opt) -> int: # return number of matches
        '''
        process a window in search mode, according to 
        '''
        debug = opt.get('debug', False)
        title = clean_text(w1.window_text())
        ct = w1.element_info.control_type
        class_name = w1.class_name()
        if debug:
            print(f"checking window: title={title}, control_type={ct}, mc1={mc1}, level2_dict={level2_dict}")
        if 'title_re' in mc1:
            if re.search(mc1['title_re'], title, re.IGNORECASE):
                if debug:
                    print(f"matched title_re={mc1['title_re']} with title={title}")
            else:
                if debug:
                    print(f"title={title} doesn't match title_re={mc1['title_re']}")
                return 0

        if 'title' in mc1:
            if mc1['title'].lower() == 'any' or mc1['title'].lower() == title.lower():
                if debug:
                    print(f"matched actual title={mc1['title']} with expected title={title}")
            else:
                if debug:
                    print(f"actual title={title} doesn't match expected title={mc1['title']}")
                return 0

        if 'control_type' in mc1:
            if mc1['control_type'].lower() == 'any' or mc1['control_type'].lower() == ct.lower():
                if debug:
                    print(f"matched actual control_type={mc1['control_type']} with expected control_type={ct}")
            else:
                if debug:
                    print(f"actual control_type={ct} doesn't match expected control_type={mc1['control_type']}")
                return 0

        if 'class_name' in mc1:
            if mc1['class_name'].lower() == 'any' or mc1['class_name'].lower() == class_name.lower():
                if debug:
                    print(f"matched actual class_name={mc1['class_name']} with expected class_name={class_name}")
            else:
                if debug:
                    print(f"actual class_name={class_name} doesn't match expected class_name={mc1['class_name']}")
                return 0

        if 'process_id' in mc1:
            pid = w1.process_id()
            if int(mc1['process_id']) == pid:
                if debug:
                    print(f"matched actual process_id={mc1['process_id']} with expected process_id={pid}")
            else:
                if debug:
                    print(f"actual process_id={pid} doesn't match expected process_id={mc1['process_id']}")
                return 0

        if 'automation_id' in mc1:
            auto_id = w1.element_info.automation_id
            if mc1['automation_id'].lower() == 'any' or mc1['automation_id'].lower() == auto_id.lower():
                if debug:
                    print(f"matched actual automation_id={mc1['automation_id']} with expected automation_id={auto_id}")
            else:
                if debug:
                    print(f"actual automation_id={auto_id} doesn't match expected automation_id={mc1['automation_id']}")
                return 0

        # if we reach here, we have a match. always print it with top window info
        top_title = clean_text(search_top_window.window_text())
        top_ct = search_top_window.element_info.control_type
        top_class = search_top_window.class_name()
        top_pid = search_top_window.process_id()

        print(f"\nunder top window: title=\"{top_title}\" control_type={top_ct} class_name={top_class} pid={top_pid}")
        print(f"  matched window: title=\"{title}\" control_type={ct} class_name={class_name}")

        if level2_dict:
            scope2 = level2_dict['scope2']
            mc2 = level2_dict['criteria_dict2']
            if scope2 == 'child':
                if debug:
                    print(f"w1.descendants()={pformat(w1.descendants())}")
                    print(f"w1.children()={pformat(w1.children())}")
                search_windows = w1.descendants()
            elif scope2 == 'all':
                if debug:
                    print(f"search_top_window.descendants()={pformat(search_top_window.descendants())}")
                search_windows = search_top_window.descendants()
            else:
                raise ValueError(f"unknown scope2={scope2}")
            
            print(f"searching level 2 windows in scope2={scope2} with criteria={mc2}")
            print(f"\n-------------- level 2 search results begin --------------")
            match_count = 0
            for w2 in search_windows:
                if debug:
                    print(f"w2 title=\"{clean_text(w2.window_text())}\" control_type={w2.element_info.control_type} class_name={w2.class_name()}")
                # recursively search level 2 windows
                match_count += self.find_process_one_window(w2, mc2, search_top_window, None, **opt)
            print(f"-------------- level 2 search results end ----------------\n")

            # if we have level 2 criteria, 'action' has been already processed in 
            # above recursive calls.
            return match_count 
        else:
            match_count = 1

        if mc1.get('action', None) == None or mc1['action'].lower() == 'print':
            pass # already printed above 
        elif mc1['action'].lower() == 'click':
            self.click_window(w1, **opt)
        elif mc1['action'].lower().startswith('type='):
            to_type = mc1['action'][5:]
            print(f"typing '{to_type}' into window: {w1}, title=\"{clean_text(title)}\" control_type={clean_text(ct)} class_name={class_name}")
            w1.type_keys(to_type, with_spaces=True, set_foreground=True)
            sleep(1)
        else:
            raise ValueError(f"unknown search action {mc1['action']}")
        
        return match_count

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

        if long_cmd == 'backend':
            if not arg in (None, 'win32', 'uia'):
                raise ValueError(f"backend must be win32 or uia, got {arg}")
            if dryrun:
                # syntax check is done now.
                return ret
            if arg is None:
                print(f"current backend is {self.backend}")
            else:
                if arg == self.backend:
                    print(f"backend is already {self.backend}, no change.")
                else:
                    print(f"changing backend from {self.backend} to {arg}")
                    self.backend = arg
                    self.app = Application(backend=self.backend)
                    self.desktop = pywinauto.Desktop(backend=self.backend)
                    self.top_window = None
                    self.current_window = None
                    self.window_and_child_specs = []
                    print(f"'app', 'desktop' will be re-initialized with the new backend.")
                    # note: changing backend will not trigger re-connect, use 'connect' command to re
        elif long_cmd == 'descendants':
            '''
            attributes:
                    depth:     max depth of children, default 5
                    timeout:       default 2s
                    count:     max number of descendants to list, default 100
                example:
                    desc               # default depth=5 from current window
                    desc=depth=1       # only the children of top window
                    desc=timeout=2
            '''
            # parse the attributes
            maxdepth=5
            maxcount=100
            timeout=2

            if arg:
                # prarse keyvalue
                kv_list = tpsup.keyvaluetools.parse_keyvalue(arg)
                for kv in kv_list:
                    k = kv['key']
                    v = kv['value']

                    if k == 'depth':
                        maxdepth = int(v)
                    elif k == 'timeout':
                        timeout = int(v)
                    elif k == 'count':
                        maxcount = int(v)
                    else:
                        raise ValueError(f"invalid descendants attribute {kv['original']}")

            if dryrun:
                # syntax check is done
                return ret

            if self.top_window is None:
                print("ERROR: top_window is None, cannot list descendants.")
                print("       use desktop and top/connect command first to connect to an app's top window.")
                ret['bad_input'] = True
            else:
                # we use self.* as global variables.
                self.descendants = []
                self.i = 0
                # start with top window and recursively print descendants
                def recursive_descendants(w: WindowSpecification, depth:int):
                    indent = '  ' * depth
                    title = clean_text(w.window_text())
                    ct = w.element_info.control_type
                    class_name = w.class_name()
                    auto_id = w.element_info.automation_id
                    print(f"{indent}{self.i} - title=\"{title}\" control_type={ct} class_name={class_name} auto_id={auto_id}")
                    self.i += 1

                    if self.i >= maxcount:
                        print(f"(reached maxcount={maxcount}, stop listing more descendants.)")
                        return
                    
                    self.descendants.append({
                        'window': w,
                        'title': title,
                        'control_type': ct,
                        'class_name': class_name,
                        'auto_id': auto_id
                    })

                    if depth >= maxdepth:
                        if w.children():
                            # only print if there are more children
                            print(f"{indent}(there are more children under but we reached maxdepth={maxdepth}.)")
                        return
                    for child in w.children():
                        recursive_descendants(child, depth=depth+1)

                recursive_descendants(self.current_window, depth=0)

                print(f"\nuse 'child=<index>' to locate a descendant window and set it as current_window.")
                print(f"use 'top' to switch current_window to top_window.")
                print(f"use 'click' to click the current_window.")
                # for descendant_window in self.current_window.descendants():
                #     print(f"desc window={pformat(descendant_window)}, "
                #           f"title={clean_text(descendant_window.window_text())}, "
                #           f"control_type={descendant_window.element_info.control_type}, "
                #           f"python={type(descendant_window).__name__}, "
                #           f"class_name={descendant_window.class_name()}")
                #     # print(f"dir(descendant_window)={dir(descendant_window)}")
                #     # print(f"element_info={pformat(descendant_window.element_info)}")
                #     # print(f"dir(element_info)={dir(descendant_window.element_info)}")
        # elif long_cmd == 'child':
        #     idx = int(arg)
        #     # max_child_specs = len(self.window_and_child_specs)
        #     num_descendants = len(self.descendants)
        #     if idx < 0 or idx >= num_descendants:
        #         print(f"invalid idx {idx}, must be between 0 and {num_descendants-1}")
        #         ret['bad_input'] = True
        #     else:
        #         # w, which, criteria_dict1 = self.window_and_child_specs[idx]
        #         # print(f"exploring child {idx}: {criteria_dict1} from {which}")
        #         # # extract args from child_window(...)

        #         # code = f"self.{which}.{criteria_dict1}"
        #         # print(f"code={code}")
        #         # self.current_window = eval(code, globals(), locals())
                
        #         # result = self.locate_cmd_arg('click', '', **opt)
        #         # ret.update(result)
        #         self.current_window = self.descendants[idx]['window']
        #         print(f"switched current_window to child {idx}: title=\"{clean_text(self.current_window.window_text())}\", control_type={self.current_window.element_info.control_type}, class_name={self.current_window.class_name()}")
        elif long_cmd == 'click':
            if self.current_window is None:
                print("current_window is None, cannot click")
                ret['bad_input'] = True
            else:
                if not self.click_window(self.current_window, **opt):
                    self.current_window = None
                    self.descendants = []  # clear descendants because current_window is gone or changed.

                # if self.current_window is not None:
                #     # after a successful click, we refresh our control identifiers tree.
                #     self.refresh_window_specs()
                #     ret['relist'] = True
        elif long_cmd == 'connect':
            '''
            connect with title_re, title
            connect=title_re=.*tianjunk.*
            connect=title="tianjunk - Notepad"
            '''
            kv_pairs = tpsup.keyvaluetools.parse_keyvalue(arg)
            conn_param_dict = {}
            for kv in kv_pairs:
                k = kv['key']
                v = kv['value']
                original = kv['original']
                if k == 'title_re':
                    if 'title' in conn_param_dict:
                        raise ValueError(f"cannot have both title and title_re in {original}")
                    conn_param_dict['title_re'] = v
                elif k == 'title':
                    if 'title_re' in conn_param_dict:
                        raise ValueError(f"cannot have both title and title_re in {original}")
                    conn_param_dict['title'] = v
                else:
                    raise ValueError(f"invalid connect arg {original}, must be title_re= or title=")
                
            if 'title_re' not in conn_param_dict and 'title' not in conn_param_dict:
                raise ValueError(f"connect arg must have title_re= or title=")
            
            # at this point, syntax check is done.
            if dryrun:
                return ret
            
            print(f"connecting to window with {conn_param_dict}, backend={self.backend}")
            self.app = Application(backend=self.backend)
            print(f"app={pformat(self.app)}")

            # if k == 'title_re':
            #     result = self.app.connect(title_re=v)
            # else:
            #     result = self.app.connect(title=v)
            result = self.app.connect(**conn_param_dict)
            print(f"after connected, result={result}")
            self.top_window = self.app.top_window()
            self.top_window.wait('visible')
            self.current_window = self.top_window
            self.top_window.click_input()  # ensure the window is focused
            sleep(1)
            print(f"connected to window with {conn_param_dict}, top_window={self.top_window}")
            # self.refresh_window_specs()
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
        elif long_cmd == 'current':
            '''
            print the current state:
            top_window
            current_window
            '''
            print(f"app.process={self.app.process}")

            if self.top_window is None:
                print("ERROR: top_window is None")
                print("       use desktop and top/connect command first to connect to an app's top window.")
                ret['bad_input'] = True
            else:
                print(f"top_window={self.get_window_spec(self.top_window)}")
                print(f"current_window={self.get_window_spec(self.current_window)}")
                print(f"top_window.process_id()={self.top_window.process_id() if self.top_window else None}")
        
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
            self.top_windows_selector = []
            i = 0
            for w in top_windows:
                title = clean_text(w.window_text())
                control_type = w.element_info.control_type
                class_name = w.class_name()
                pid = w.process_id()
                auto_id = w.element_info.automation_id
                if debug:
                    print(f"desktop top window={pformat(w)}")
                if title_filter is None or re.search(title_filter, title, re.IGNORECASE):
                    self.top_windows_selector.append(
                        {
                            'window': w, 
                            'title': title, 
                            'control_type': control_type, 
                            'class_name': class_name, 
                            'pid': pid,
                            'auto_id': auto_id,
                        }
                    )
                    print(f"{i} - top window, conn=title=\"{title}\"\n    control_type={control_type}, class_name={class_name}, pid={pid}, auto_id={auto_id}")
                    i += 1
            print(f"\nuse top=<index> or connect=title=... to connect to one of the top windows.")
        elif long_cmd == 'find':
            '''
            find=criterias
            find=scope=<scope> title_re=<title_re> title=<title> type=<control_type> class=<class_name> action=<action>

            separator is space.
            '''
            # parse arg into a dict
            criteria_list = tpsup.keyvaluetools.parse_keyvalue(arg)
            criteria_dict1 = {}
            criteria_dict2 = {}

            scope1 = 'top' # default scope
            scope2 = None

            action = None
            timeout = 5 # seconds

            for c in criteria_list:
                k = c['key']
                v = c['value']
                original = c['original']

                if k == 'scope':
                    if v not in ['desktop', 'top', 'current']:
                        raise ValueError(f"invalid scope={v} in criteria={original}, must be one of desktop, top, current")
                    scope1 = v
                elif k == 'scope2':
                    if v not in ['child', 'all']:
                        raise ValueError(f"invalid scope2={v} in criteria={original}, must be one of child, all")                
                    scope2 = v
                elif k == 'timeout':
                    try:
                        to = int(v)
                        if to <= 0:
                            raise ValueError
                    except ValueError:
                        raise ValueError(f"invalid timeout={v} in criteria={original}, must be a positive integer")
                    timeout = to
                elif k == 'title_re':
                    if 'title' in criteria_dict1:
                        raise ValueError(f"cannot have both title and title_re in criteria={original}")
                    criteria_dict1['title_re'] = v
                elif k == 'title_re2':
                    if 'title2' in criteria_dict2:
                        raise ValueError(f"cannot have both title2 and title_re2 in criteria={original}")
                    criteria_dict2['title_re'] = v
                elif k == 'title':
                    if 'title_re' in criteria_dict1:
                        raise ValueError(f"cannot have both title and title_re in criteria={original}")
                    criteria_dict1['title'] = v
                elif k == 'title2':
                    if 'title_re' in criteria_dict2:
                        raise ValueError(f"cannot have both title2 and title_re2 in criteria={original}")
                    criteria_dict2['title'] = v
                elif k == 'type':
                    criteria_dict1['control_type'] = v
                elif k == 'type2':
                    criteria_dict2['control_type'] = v
                elif k == 'class':
                    criteria_dict1['class_name'] = v
                elif k == 'class2':
                    criteria_dict2['class_name'] = v
                elif k == 'action':
                    if v.lower() not in ['print', 'click'] and not v.lower().startswith('type='):
                        raise ValueError(f"invalid action={v} in criteria={original}, must be one of print, click, type=...")
                    action = v
                elif k == 'pid':
                    try:
                        pid = int(v)
                        if pid <= 0:
                            raise ValueError
                    except ValueError:
                        raise ValueError(f"invalid pid={v} in criteria={original}, must be a positive integer")
                    criteria_dict1['process_id'] = pid
                elif k == 'auto_id':
                    criteria_dict1['automation_id'] = v
                elif k == 'auto_id2':
                    criteria_dict2['automation_id'] = v
                else:
                    raise ValueError(f"invalid criteria key={k} in criteria={original}")
            
            if debug:
                print(f"parsed criteria_dict1={criteria_dict1},\n criteria_dict2={criteria_dict2}, scope={scope1}")

            if scope2 and not criteria_dict2:
                raise ValueError(f"scope2={scope2} is given, but no level 2 criteria is given.")
            if criteria_dict2 and not scope2:
                scope2 = 'all' # default scope2

            if scope2:
                criteria_dict2['action'] = action
                level2_dict = {
                    'scope2': scope2,
                    'criteria_dict2': criteria_dict2,
                }
            else:
                criteria_dict1['action'] = action
                level2_dict = None
                
            # at this point, syntax check is done.
            if dryrun:
                return ret

            if scope1 == 'desktop':
                search_windows = self.desktop.windows()
            elif scope1 == 'top':
                if self.top_window is None:
                    print("ERROR: top_window is None, cannot search in 'top' scope")
                    print("       use desktop and top/connect command first to connect to an app's top window.")
                    ret['bad_input'] = True
                    return ret
                search_windows = [self.top_window]
            else:  # current
                if self.current_window is None:
                    print("current_window is None, cannot search in 'current' scope")
                    ret['bad_input'] = True
                    return ret
                search_windows = [self.current_window]

            print(f"searching windows in scope={scope1} with criteria={criteria_dict1}, level2_dict={level2_dict}")
            print(f"\n-------------- search results begin --------------")
            for w in search_windows:
                if scope1 in ['top', 'desktop']:
                    search_top_window = w
                else:
                    # scope == 'current'
                    search_top_window = self.top_window
                # recursively search the window and its descendants
                self.match_count = self.find_process_one_window(w, criteria_dict1, search_top_window, level2_dict, **opt)

                def long_search():
                    count = 0
                    for dw in w.descendants():
                        self.match_count += self.find_process_one_window(dw, criteria_dict1, search_top_window, level2_dict, **opt)
                        count += 1
                        if count %100 == 0 and debug:
                            print(f"checked {count} descendant windows...")          

                thread = threading.Thread(target=long_search)
                thread.start()
                thread.join(timeout=timeout)
                if thread.is_alive():
                    w_title = clean_text(w.window_text())
                    w_ct = w.element_info.control_type
                    w_class = w.class_name()
                    w_auto_id = w.element_info.automation_id
                    w_pid = w.process_id()
                    print(f"search timeout after {timeout}s, skipping children of window title={w_title}, control_type={w_ct}, class_name={w_class}, auto_id={w_auto_id}, pid={w_pid}")
            print(f"-------------- search results end ----------------\n")
            if self.match_count > 0:
                if scope1 == 'desktop':
                    print(f"scope1=desktop, use desktop+top or connect command to connect to the matched top window.")
        elif long_cmd == 'list':
                self.display()
        elif long_cmd == 'child':
            '''
                child=<index>       # if integer, switch current_window to the 'descendants' index.
                child=top           # switch current_window to top_window
                child=child_spec    # switch current_window to top_window's child window matching child_spec.
            '''

            if self.top_window is None:
                print("ERROR: top_window is None, cannot locate")
                print("       use desktop and top/connect command first to connect to an app's top window.")
                ret['bad_input'] = True
                return ret
            
            if self.descendants is None:
                print("ERROR: descendants is None, please run 'descendants' command first.")
                ret['bad_input'] = True
                return ret
            
            # if arg is integer, switch to that index in window_and_child_specs
            if arg.isdigit():
                idx = int(arg)
                # max_child_specs = len(self.window_and_child_specs)
                num_descendants = len(self.descendants)
                if idx < 0 or idx >= num_descendants:
                    print(f"invalid idx {idx}, must be between 0 and {num_descendants-1}")
                    ret['bad_input'] = True
                else:
                    # w, which, criteria_dict1 = self.window_and_child_specs[idx]
                    # print(f"exploring child {idx}: {criteria_dict1} from {which}")
                    # # extract args from child_window(...)

                    # code = f"self.{which}.{criteria_dict1}"
                    # print(f"code={code}")
                    # self.current_window = eval(code, globals(), locals())
                    
                    # result = self.locate_cmd_arg('click', '', **opt)
                    # ret.update(result)
                    self.current_window = self.descendants[idx]['window']
                    self.descendants = []  # clear descendants because current_window is changed.
                    print(f"switched current_window to child {idx}: title=\"{clean_text(self.current_window.window_text())}\", control_type={self.current_window.element_info.control_type}, class_name={self.current_window.class_name()}")

            elif arg.lower() == 'top':
                self.current_window = self.top_window
                self.descendants = []  # clear descendants because current_window is changed.
                print(f"switched current_window to top_window: title=\"{clean_text(self.current_window.window_text())}\", control_type={self.current_window.element_info.control_type}, class_name={self.current_window.class_name()}")
            else:
                '''
                child_spec is a string like 
                    title="OK" control_type="Button", 
                    title_re=.*Notepad.*
                    title="Untitled - Notepad" control_type=Edit
                
                keys can be:
                    title
                    title_re
                    control_type
                    class_name

                quotes around title value are optional.

                we need to parse the string into a dict.
                '''
                parts = tpsup.keyvaluetools.parse_keyvalue(v)

                criteria_dict1 = {}
                for p in parts:
                    k, v = p.split('=', 1)
                    k = k.strip()
                    v = v.strip()

                    # remove ", " if it is in the front of key
                    # eg, in title=OK, control_type=Button
                    k = re.sub(r',\s*', '', k)

                    if k not in ['title', 'title_re', 'control_type', 'class_name']:
                        raise ValueError(f"invalid child_spec key {k}, must be one of title, title_re, control_type, class_name")
                    # remove quotes if any
                    if (v.startswith('"') and v.endswith('"')) or \
                        (v.startswith("'") and v.endswith("'")):
                        v = v[1:-1]
                    elif (v.startswith('"') and not v.endswith('"')) or \
                            (v.startswith("'") and not v.endswith("'")):
                        raise ValueError(f"unmatched quote in {k}={v}")
                    criteria_dict1[k.strip()] = v.strip()
                print(f"parsed child_spec = {criteria_dict1}")
                # syntax check is done at this point.
                if dryrun:
                    return ret

                self.current_window = self.top_window.child_window(**criteria_dict1)
                if not self.click_window(self.current_window, **opt):
                    self.current_window = None
                    self.descendants = []  # clear descendants because current_window is gone or changed.
                    print(f"failed to locate child_spec {criteria_dict1} from {k}")
                    ret['bad_input'] = True
                # if self.current_window is not None:
                #     # after a successful click, we refresh our control identifiers tree.
                #     self.refresh_window_specs()
                #     ret['relist'] = True
                # else:
                
                    # print(f"failed to locate child_spec {criteria_dict1} from {k}")
                    # ret['bad_input'] = True
        # elif long_cmd == 'refresh':
        #     self.refresh_window_specs()
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
                self.descendants = []  # clear descendants because current_window is changed.
                self.top_window.wait('visible')
                self.top_window.click_input()  # ensure the window is focused
                sleep(1)
                # self.refresh_window_specs()
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
                    print(f"    {w}, title={clean_text(w.window_text())}, {pformat(w)}")

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
                        print(f"   title={clean_text(w.window_text())}, control_type={w.element_info.control_type}, {pformat(w)}")
                    return ret
                    
                self.current_window = self.top_window
                self.descendants = []  # clear descendants because current_window is changed.

                # AttributeError: 'UIAWrapper' object has no attribute 'wait'
                # self.top_window.wait('visible')
                if isinstance(self.top_window, UIAWrapper):
                    self.top_window = self.get_windowspec_from_uiawrapper(self.top_window)
                self.top_window.wait('visible')
                
                self.top_window.click_input()  # ensure the window is focused
                sleep(1)
                # self.refresh_window_specs()
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
            top=<index>
            '''
            if not arg:
                # set current_window to top_window
                if self.top_window is None:
                    print("ERROR: top_window is None")
                    print("       use desktop and top/connect command first to connect to an app's top window.")
                else:
                    self.current_window = self.top_window
                    self.descendants = []  # clear descendants because current_window is changed.
                    print(f"set current_window to top_window")
                    # self.refresh_window_specs()
                    # ret['relist'] = True
            else:
                # set current_window to the top window of the desktop with index arg
                if not self.top_windows_selector:
                    print("top_windows_selector is empty, please run 'desktop' command first")
                    ret['bad_input'] = True
                else:
                    try:
                        idx = int(arg)
                    except ValueError:
                        print(f"invalid index {arg}, must be an integer")
                        ret['bad_input'] = True
                        return ret
                    max_idx = len(self.top_windows_selector) - 1
                    if idx < 0 or idx > max_idx:
                        print(f"invalid index {idx}, must be between 0 and {max_idx}")
                        ret['bad_input'] = True
                    else:
                        w = self.top_windows_selector[idx]['window']
                        title = self.top_windows_selector[idx]['title']
                        print(f"setting current_window and top_window to top window of the desktop with index {idx}, title={title}")
                        
                        # the following line causes error:
                        #     AttributeError: 'UIAWrapper' object has no attribute 'wait'
                        # self.current_window = w
                        # self.top_window = w
                        
                        # the following causes error:
                        #     Please use start or connect before trying anything else
                        # if isinstance(w, UIAWrapper):
                        #     w = self.get_windowspec_from_uiawrapper(w)
                        # self.current_window = w
                        # self.top_window = w

                        # we have to connect to the window because it is a separate process.
                        self.top_window = self.app.connect(handle=w.handle).window(handle=w.handle)
                        self.current_window = self.top_window
                        self.descendants = []  # clear descendants because current_window is changed.

                        try:
                            self.current_window.wait('visible')
                            self.current_window.click_input()  # ensure the window is focused
                            sleep(1)
                            
                            # self.refresh_window_specs()
                            # ret['relist'] = True
                        except pywinauto.findwindows.ElementNotFoundError as e:
                            print(f"ElementNotFoundError: current_window is not valid, either closed or you need to wait longer.")
                            ret['bad_input'] = True
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

    def get_window_spec(self, w: WindowSpecification, **opts) -> dict:
        '''
        return the window spec as a dict.
        example:
            {
                'title': 'Untitled - Notepad',
                'control_type': 'Window',
                'class_name': 'Notepad',
                'title_re': '.*Notepad.*'
            }
        '''

        debug = opts.get('debug', 0)
        full_title = clean_text(w.window_text())
        ct = w.element_info.control_type
        cn = w.element_info.class_name
        title_re = None

        # title_re is a shorter version of title, in particular, if title is too long.
        # when we come up with title_re, we try to remove escaped chars, quotes, ...
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
            title_re=f".*{longest_short_title}.*"

        return {
            'title': full_title,
            'control_type': ct,
            'class_name': cn,
            'title_re': title_re,
        }
        
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

def clean_text(s: str, **opt) -> str:
    '''
    convert all weird chars into '.' for better display.
    '''
    newchar = opt.get('newchar', '.')
    max_len = opt.get('max_len', 300)
    if len(s) > max_len:
        s = s[:max_len] + "...(truncated)"

    # remove weird chars
    s = re.sub(r'[^0-9a-zA-Z \'\"\\~!@#%^&*:<>.,()=\t_-]', newchar, s, flags=re.DOTALL)
    return s

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
