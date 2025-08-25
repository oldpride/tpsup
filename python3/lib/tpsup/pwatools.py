import io
import re
import sys
from time import sleep
import pywinauto
from pywinauto.application import Application, WindowSpecification
from pywinauto.controls.uiawrapper import UIAWrapper

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
        'need_args': 1,
        'usage': '''
            c 1
            ''',
    },
    'help': {
        'short': 'h',
        'usage': '''
            h
            h type
        ''',
    },
    'quit': {
        'short': 'q',
        'usage': '''
            q
        ''',
    },
    'refresh': {
        'short': 'r',
        'usage': '''
            refresh the child window list
            r
        ''',
    },
    'script': {
        'short': 'sc',
        'need_args': 1,
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
    'type': {
        'short': 't',
        'need_args': 1,
        'usage': '''
            t hello world
            t {UP}
            t {ENTER}
            t {F5}
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
    
    app = Application(
        # backend="win32", # win32 is the default.
        backend="uia", # uia is modern and preferred.
    )

    print(f"Connecting app with title_re=\"{title_re}\"...")

    app.connect(title_re=title_re, timeout=10)

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
            refresh = result.get('refresh', )
            if go_back or refresh:
                break
        if go_back:
            break

init_ret = {
    'break': False,
    'bad_input': False,
    'refresh': False
}

def locate(user_input: str, **opt):
    debug = opt.get('debug', False)
    verbose = opt.get('verbose', 0)

    global window_and_child_specs
    global current_window
    global top_window
    
    ret = init_ret.copy()

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

    if need_args and not args:
        print(f"command '{command}' needs args")
        ret['bad_input'] = True
        return ret
    elif not need_args and args:
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
    elif long_cmd == 'quit':
        print("bye")
        go_back = True
        ret['break'] = True
    elif long_cmd == 'refresh':
        print("refreshing the child window list...")
        ret['refresh'] = True
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
    
    ret = init_ret.copy()

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
        refresh = result.get('refresh', )
        if go_back:
            print("script terminated by quit command")
            break
        if refresh:
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
