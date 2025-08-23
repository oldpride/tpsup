import io
import re
import sys
from time import sleep
from pywinauto.application import Application, WindowSpecification
from pywinauto.controls.uiawrapper import UIAWrapper

from typing import Union

app:Application = None

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

#    |    | child_window(title="Maximize", control_type="Button")
regex_child_window = re.compile(r".*?(child_window\(.+?\))", re.MULTILINE|re.DOTALL)

w2 = None

def explore_child(o: Union[Application, WindowSpecification, UIAWrapper]) -> None:
    print(f"\nexplore_child input's python class name={type(o).__name__}")

    global app
    if isinstance(o, Application):
        app = o
        top_window = app.top_window()

        print(f"top_window's python class name={type(top_window).__name__}")

        top_window.wait('visible')
        top_window.click_input()  # ensure the window is focused
        sleep(1)
    
      
        print(f"exploring top window")
        explore_child(top_window)
    elif isinstance(o, WindowSpecification) or isinstance(o, UIAWrapper):
        if isinstance(o, UIAWrapper):
            w = get_windowspec_from_uiawrapper(o)
        else:
            w = o
        # w.wait('visible')
        # w.click_input()  # ensure the window is focused
        # sleep(1)
        dump_window(w)
        ci_string = get_control_identifiers(w)
        i=0
        children = []
        multiline = ci_string
        # extract line like: child_window(title="\rhello\rworld\r", control_type="Document")
        # note this is a multi-line match because title can contain \r which is a line break.
        while m := regex_child_window.match(multiline):
            child_spec = m.groups()[0]
            multiline = multiline[m.end():] # leftover string to be processed

            # example of child_spec:
            #   child_window(title="\rcurrent time=2025-08-23 02:40:46\r9:40 PM 8/22/2025", control_type="Document")
            # notice that the child_spec's title can contain \r which is a line break.
            # we should pick a substring of title that doesn't contain \r.
            # also we should reduce the length of title to at most 30 characters.
            title_match = re.search(r'title="(.*?)"', child_spec, re.DOTALL)
            if title_match:
                full_title = title_match.groups()[0]
                short_titles = full_title.split('\r')
                # pick the longest substring
                short_title = max(short_titles, key=len)
                if len(short_title) > 30:
                    short_title = short_title[:30]
                title_part = f"title_re=\".*{short_title}.*\""
                # replace the title part in child_spec
                child_spec = re.sub(r'title=".*?"', title_part, child_spec)
            print(f"  {i}: {child_spec}")
            i += 1
            children.append(child_spec)
            

        while True:
            # get user input
            user_input = input(f"num-child, q-go back: ")
            if user_input.lower() == 'q':
                print("bye")
                break
            elif user_input.isdigit():
                num = int(user_input)
                if num < 0 or num >= i:
                    print(f"invalid num {num}")
                else:
                    child = children[num]
                    print(f"exploring child {num}: {child}")
                    # extract args from child_window(...)
                    global w2
                    exec(f"w2 = w.{child}")
                    w2.click_input()
                    sleep(1)
                    explore_child(w2)
            else:
                print(f"invalid input {user_input}")
    else:
        raise TypeError(f"Expected Application, WindowSpecification or UIAWrapper, got {type(w)}")

    return
    