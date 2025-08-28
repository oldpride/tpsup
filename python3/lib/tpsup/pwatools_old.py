import io
import re
import sys
from time import sleep
import pywinauto
from pywinauto.application import Application, WindowSpecification
from pywinauto.controls.uiawrapper import UIAWrapper
from tpsup.cmdtools import run_cmd
import tpsup.exploretools

from typing import Union

def dump_window(o: Union[WindowSpecification, UIAWrapper]) -> None:
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

def get_windowspec_from_uiawrapper(u: UIAWrapper) -> WindowSpecification:
    '''
    get the WindowSpecification from a UIAWrapper.
    '''
    global app
    if app is None:
        raise ValueError("app must be provided")
    handle = u.handle
    w:WindowSpecification = app.window(handle=handle)
    return w

def get_control_identifiers(o: Union[WindowSpecification, UIAWrapper]) -> str:
    '''
    return the control identifiers as a string.
    by default, print_control_identifiers prints to stdout.
    '''
    # Create a StringIO object to capture the output
    old_stdout = sys.stdout
    redirected_output = io.StringIO()
    sys.stdout = redirected_output

    if isinstance(o, UIAWrapper):
        w = get_windowspec_from_uiawrapper(o)
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

usage = {
    'child': {
        'short': 'c',
        'need_args': True,
        'usage': '''
            c 1
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
    'refresh': {
        'short': 'r',
        'no_args': True,
        'usage': '''
            refresh the child window list
            r
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
            ty hello world
            ty {UP}
            ty {ENTER}
            ty {F5}
        ''',
    },
}

usage_by_short = {}
window_and_child_specs = []
app = None
top_window = None
current_window = None

def get_prompt() -> str:
    prompt = ""
    for k in sorted(usage.keys()):
        v = usage[k]
        short = v.get('short', k)
        prompt += f"{short}-{k} "
    return prompt


def refresh_window_specs(**opt):
    global window_and_child_specs
    global top_window
    global current_window

    debug = opt.get('debug', False)

    top_window_child_specs = get_child_specs(top_window, debug=debug)

    window_and_child_specs = []  # list of (window, which, child_spec)
    for s in top_window_child_specs:
        window_and_child_specs.append( (top_window, 'top_window', s) )

    if current_window and current_window != top_window:
        current_window_child_specs = []
        try:
            current_window_child_specs = get_child_specs(current_window, debug=debug)
        except pywinauto.findwindows.ElementNotFoundError as e:
            print(f"ElementNotFoundError: current_window is not valid, either closed or you need to wait longer.")
            return
        
        for s in current_window_child_specs:
            window_and_child_specs.append( (current_window, 'current_window', s) )

def explore_app(**opt) -> None:
    debug = opt.get('debug', False)
    verbose = opt.get('verbose', 0)
    title_re = opt.get('title_re', None)

    global window_and_child_specs
    global app
    global top_window
    global current_window

    if title_re is None:
        raise ValueError("title_re is required")
    
    app = None

    backend = opt.get('backend', 'uia')

    connected = False
    cmd1 = opt.get('command1', None)
    if cmd1:
        print(f"startup command: {cmd1}")
        app = Application(
            # backend="win32", # win32 is the default.
            # backend="uia", # uia is modern and preferred.
            backend=backend,
        )
        connected = True
        app.start(cmd1, wait_for_idle=False)
        sleep(2)  # wait for the app to start
    else:
        app = Application(
            # backend="win32", # win32 is the default.
            # backend="uia", # uia is modern and preferred.
            backend=backend,
        )

        print(f"Connecting app with title_re=\"{title_re}\"...")
        
        try:
            app.connect(title_re=title_re, timeout=10)
            connected = True
        except Exception as e:
            print(f"Failed to connect to app: {e}")

        if not connected:
            # try to start it
            cmd2 = opt.get('command2', None)
            if cmd2:
                print(f"Starting app with command: {cmd2}")
                # run_cmd(cmd2)
                app.start(cmd2, wait_for_idle=False)
                sleep(2) # wait for the app to start
                # print(f"connecting app with title_re=\"{title_re}\"...")
                # app.connect(title_re=title_re, timeout=10)
            else:
                print(f"No startup command provided.")
                return

    print(f"Connected to app")
    print(f"\nexplore_app input's python class name={type(app).__name__}")

    top_window = app.top_window()

    print(f"top_window's python class name={type(top_window).__name__}")

    top_window.wait('visible')
    top_window.click_input()  # ensure the window is focused
    sleep(1)

    global usage_by_short
    for k, v in usage.items():
        short = v.get('short', k)
        usage_by_short[short] = v
        v['long'] = k

    current_window = top_window

    script = opt.get('script', None)
    if script:
        print(f"running script file: {script}")
        result = run_script(script, **opt)
        if result.get('break', False):
            return
    
    # after running the script, we continue to interactive mode.
    while True:
        refresh_window_specs()

        i = 0
        
        for w, which, s in window_and_child_specs:
            print(f"{i}: {which}.{s}")
            i += 1

        go_back = False
        while True: # loop until we get valid input
            # get user input
            user_input = input(get_prompt() + ": ")

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
            result = locate(user_input)
            go_back = result.get('break', False)
            relist = result.get('relist', False)
            if go_back or relist:
                break
        if go_back:
            break

ret0 = {
    'break': False,
    'bad_input': False,
    'relist': False
}

def locate(user_input: str, **opt):
    debug = opt.get('debug', False)
    verbose = opt.get('verbose', 0)

    global window_and_child_specs
    global current_window
    global top_window
    
    ret = ret0.copy()

    command, args, *_ = user_input.split(' ', 1) + [None] # unpack unpredictable number of values
    print(f"command='{command}', args='{args}'")
    if command in usage_by_short:
        v = usage_by_short.get(command, None)
    else:
        v = usage.get(command, None)

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

    if long_cmd == 'child':
        idx = int(args)
        max_child_specs = len(window_and_child_specs)
        if idx < 0 or idx >= max_child_specs:
            print(f"invalid idx {idx}, must be between 0 and {max_child_specs-1}")
            ret['bad_input'] = True
        else:
            w, which, child_spec = window_and_child_specs[idx]
            print(f"exploring child {idx}: {child_spec} from {which}")
            # extract args from child_window(...)

            code = f"{which}.{child_spec}"
            print(f"code={code}")
            current_window = eval(code, globals(), locals())
            # w2 = w.child_window( control_type="Document")
            
            try: 
                current_window.click_input()
                sleep(1)
            except pywinauto.timings.TimeoutError as e:
                print(f"TimeoutError: child spec didn't appear in time.")
                current_window = None
            except pywinauto.findwindows.ElementNotFoundError as e:
                print(f"ElementNotFoundError: child spec is not valid, either closed or you need to wait longer.")
                current_window = None

            if current_window is not None:
                # after a successful click, we refresh our control identifiers tree.
                refresh_window_specs()
                ret['relist'] = True
    elif long_cmd == 'control_identifiers':
        if current_window is None:
            print("current_window is None, cannot get control identifiers")
            ret['bad_input'] = True
        else:
            try:
                ci_string = get_control_identifiers(current_window)
                print(f"current_window control identifiers:\n{ci_string}")
            except pywinauto.findwindows.ElementNotFoundError as e:
                print(f"ElementNotFoundError: current_window is not valid, either closed or you need to wait longer.")
                ret['bad_input'] = True
    elif long_cmd == 'help':
        if args is not None:
            if args in usage:
                print(f"help for '{args}':")
                print(usage[args]['usage'])
            elif args in usage_by_short:
                long_name = usage_by_short[args]['long']
                print(f"help for '{args}' ({long_name}):")
                print(usage[long_name]['usage'])
            else:
                print(f"unknown help topic '{args}'")
        else:
            print("available commands:")
            for k in sorted(usage.keys()):
                v = usage[k]
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
        print("refreshing the child window list tree...")
        refresh_window_specs()
        ret['relist'] = True
    elif long_cmd == 'script':
        script_file = args
        result = run_script(script_file)
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
        result = run_script(lines)
        ret.update(result)
    elif long_cmd == 'text':
        if current_window is None:
            print("current_window is None, cannot get text")
            ret['bad_input'] = True
        else:
            try:
                texts = current_window.texts()
                print(f"current_window texts={texts}")
            except pywinauto.findwindows.ElementNotFoundError as e:
                print(f"ElementNotFoundError: current_window is not valid, either closed or you need to wait longer.")
                ret['bad_input'] = True
    elif long_cmd == 'top':
        current_window = top_window
        print("current_window is now top_window")
    elif long_cmd == 'type':
        current_window.type_keys(args, with_spaces=True, pause=0.05)
    else:
        print(f"invalid input {user_input}")
        ret['bad_input'] = True
    
    return ret

def run_script(script: Union[str, list], **opt):
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
    
    ret = ret0.copy()

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
        result = locate(line, **opt)

        go_back = result.get('break', False)
        relist = result.get('relist', False)
        if go_back:
            print("script terminated by quit command")
            break
        if relist:
            refresh_window_specs(**opt)

    return ret

def get_child_specs(w: WindowSpecification, **opts) -> list[str]:
    '''
    return the list of child specs as strings.
    each child spec is like: child_window(title="Maximize", control_type="Button")
    '''

    debug = opts.get('debug', False)
    ci_string = get_control_identifiers(w)
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
