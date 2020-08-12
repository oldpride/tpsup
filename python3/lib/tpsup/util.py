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


def tplog(message:str= None, file=sys.stderr, **opt):
    if message is None:
        message = ''
    timestamp = strftime("%Y-%m-%d %H:%M:%S", gmtime())

    # print(pformat(caller)) *o
    # FrameInfo(frame=<frame object at 0x7f0ce4e87af8>, filename='util.py', lineno=176, function='tplog',
    # code_context=['    caller = inspect.stack()\n'], index=0),
    # FrameInfo(frame=<frame object at 0x7f0ce4a84048>, filename='util.py', lineno=182, function='main',
    # code_context=["    tplog('test')\n"], index=0),
    # FrameInfo(frame=<frame object at 0x12e3428>, filename='util.py', lineno=185, function='<module>',
    # code_context=['    main()\n'], index=0)]
    caller = inspect.stack()[1]

    print(f"{timestamp} {os.path.basename(caller.filename)},{caller.lineno},{caller.function} {message}", file=file, **opt)


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
    print('------ test tplog')
    tplog('hello world')

    print('------ test print_exception')
    try:
        raise RuntimeError("test exception")
    except Exception as e:
        print_exception(e)
        tplog(print_exception(e, file=str))




if __name__ == '__main__':
    main()
