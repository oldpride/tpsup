import functools
import inspect
import io
import os
import sys
import traceback
from time import strftime, gmtime


def silence_BrokenPipeError(func):
    ''' replace build-in functions'''
    @functools.wraps(func)
    def silenced(*args, **kwargs):
        result = None
        try:
            result = func(*args, **kwargs)
        except BrokenPipeError:
            sys.exit(1)
        return result

    return silenced


def tplog(message:str= None, file=sys.stderr, prefix:str="time,caller"):
    if message is None:
        message = ''

    need_prefix = set(prefix.split(','))

    if 'time' in need_prefix:
        timestamp_part = f'{strftime("%Y-%m-%d %H:%M:%S", gmtime())} '
    else:
        timestamp_part = ''

    if 'caller' in need_prefix:
        # print(pformat(caller)) *o
        # FrameInfo(frame=<frame object at 0x7f0ce4e87af8>, filename='util.py', lineno=176, function='tplog',
        # code_context=['    caller = inspect.stack()\n'], index=0),
        # FrameInfo(frame=<frame object at 0x7f0ce4a84048>, filename='util.py', lineno=182, function='main',
        # code_context=["    tplog('test')\n"], index=0),
        # FrameInfo(frame=<frame object at 0x12e3428>, filename='util.py', lineno=185, function='<module>',
        # code_context=['    main()\n'], index=0)]
        caller = inspect.stack()[1]
        caller_part = f'{os.path.basename(caller.filename)},{caller.lineno},{caller.function} '
    else:
        caller_part = ''

    print(f"{timestamp_part}{caller_part}{message}", file=file)


def print_exception(e: Exception, stacktrace=True, **opt):
    file = opt.get('file', sys.stderr)

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


def main():
    print('\n------ test tplog')
    tplog('hello world')

    print('\n------ test a short version of tplog')
    tplog('hello world', prefix='time')

    print('\n------ test print_exception')
    try:
        raise RuntimeError("test exception")
    except Exception as e:
        print_exception(e)
        tplog(print_exception(e, file=str))




if __name__ == '__main__':
    main()
