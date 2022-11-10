import functools
import inspect
import io
import os
import re
import sys
import traceback
from time import strftime, gmtime


def silence_BrokenPipeError(func):
    """replace build-in functions"""

    @functools.wraps(func)
    def silenced(*args, **kwargs):
        result = None
        try:
            result = func(*args, **kwargs)
        except BrokenPipeError:
            sys.exit(1)
        return result

    return silenced


def tplog(message: str = None, file=sys.stderr, prefix: str = "time,caller"):
    if message is None:
        message = ""

    need_prefix = set(prefix.split(","))

    if "time" in need_prefix:
        timestamp_part = f'{strftime("%Y-%m-%d %H:%M:%S", gmtime())} '
    else:
        timestamp_part = ""

    if "caller" in need_prefix:
        # print(pformat(caller)) *o
        # FrameInfo(frame=<frame object at 0x7f0ce4e87af8>, filename='util.py', lineno=176, function='tplog',
        # code_context=['    caller = inspect.stack()\n'], index=0),
        # FrameInfo(frame=<frame object at 0x7f0ce4a84048>, filename='util.py', lineno=182, function='main',
        # code_context=["    tplog('test')\n"], index=0),
        # FrameInfo(frame=<frame object at 0x12e3428>, filename='util.py', lineno=185, function='<module>',
        # code_context=['    main()\n'], index=0)]
        caller = inspect.stack()[1]
        caller_part = (
            f"{os.path.basename(caller.filename)},{caller.lineno},{caller.function} "
        )
    else:
        caller_part = ""

    print(f"{timestamp_part}{caller_part}{message}", file=file)


def print_exception(e: Exception, stacktrace=True, **opt):
    file = opt.get("file", sys.stderr)

    sio = None
    if file == str:
        # print to string
        sio = io.StringIO()
        file = sio
    if stacktrace:
        print(traceback.format_exc(), file=file)
    else:
        # print("{0}: {1!r}".format(type(e).__name__, e.args), file=file, **opt)
        print("{0}: {1}".format(type(e).__name__, ";".join(e.args)), file=file, **opt)

    if sio:
        string = sio.getvalue()
        sio.close()
        return string


def tplog_exception(e: Exception, **opt):
    tplog(print_exception(e, file=str), **opt)


def convert_to_uppercase(h, **opt):
    # convert key or key/value to upper case
    if h is None:
        return h

    if type(h) == str:
        if opt.get("ConvertValue", False):
            return h.upper()
        else:
            return h
    elif type(h) == dict:
        d2 = {}
        for k, v in h.items():
            if opt.get("ConvertKey", False):
                k2 = k.upper()
            else:
                k2 = k

            v2 = convert_to_uppercase(v, **opt)

            d2[k2] = v2
        return d2
    elif type(h) == list:
        l2 = []
        for e in h:
            l2.append(convert_to_uppercase(e, **opt))
        return l2
    else:
        return h


step_count = 0

def hit_enter_to_continue(initial_steps=0, helper:dict={}):
    # helper example, see seleniumtools.py
    # helper = {
    #     'd' : ["dump page", dump, {'driver':driver, 'outputdir_dir' : tmpdir} ],
    # }
    global step_count
    if initial_steps:
        step_count = initial_steps

    if step_count > 0:
        step_count -= 1
    else:
        hint = f"Hit Enter to continue; a number to skip steps; q to quit"
        for k,v in helper.items():
            hint += f"; {k} to {v[0]}"
        hint += " : "

        answer = input(hint)
        if m := re.match(r"(\d+)", answer):
            # even if only capture 1 group, still add *_; other step_count would become list, not scalar
            step_count_str, *_ = m.groups()
            step_count = int(step_count_str)
        elif m := re.match("([qQ])", answer):
            print("quit")
            quit(0) # same as exit
        elif helper: # test dict empty
            matched_helper = False
            for k, v in helper.items():
                if m := re.match(k, answer):
                    func = v[1]
                    args = v[2]
                    func(**args)
                    matched_helper = True
                    break
            if matched_helper:
                # call recursively to get to the hint line
                hit_enter_to_continue(initial_steps, helper)

compiled_scalar_var_pattern = re.compile(r"{{([0-9a-zA-Z._-]+)}}")


def resolve_scalar_var_in_string(string: str, dict: dict, **opt):
    verbose = opt.get("verbose", 0)

    if not string:
        return string
    scalar_vars = compiled_scalar_var_pattern.findall(string)

    if not scalar_vars:
        return string

    for var in scalar_vars:
        value = dict.get(var, None)
        if value is not None:
            string = string.replace("{{" + var + "}}", f"{value}")
            if verbose:
                print(f"replaced {{{var}" + f"}} with {value}")

    return string


def print_string_with_line_numer(string: str):
    lines = string.split("\n")
    for (number, line) in enumerate(lines):
        print(f"{number+1:3} {line}")


def main():
    print("\n------ test tplog")
    tplog("hello world")

    print("\n------ test a short version of tplog")
    tplog("hello world", prefix="time")

    print("\n------ test print_exception")
    try:
        raise RuntimeError("test exception")
    except Exception as e:
        print_exception(e)
        tplog(print_exception(e, file=str))

    test = 'resolve_scalar_var_in_string("{{v1}} and {{v2}}", {"v1":"hello", "v2":1}, verbose=1)'
    print(f"---- test {test} -----")
    print(f"result={eval(test)}")


if __name__ == "__main__":
    main()
