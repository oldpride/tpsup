import functools
import functools
import multiprocessing
import multiprocessing.connection
import os
import signal
import sys
import time
import traceback
from pprint import pformat
from typing import Union, Callable

from tpsup.util import print_exception


def top_level_sleep_and_tick(duration: int, *args, **opt)-> str:
    """
    this is a test function. used to be in main(), but I got error
        AttributeError: Can't pickle local object 'main.<locals>.sleep_and_tick'
    reason:
        Pickling actually only saves the name of a function and unpickling
        requires re-importing the function by name. For that to work, the
        function needs to be defined at the top-level, nested functions won't
        be importable by the child and already trying to pickle them raises an
        exception
    therefore, I moved it outside
    :param duration:
    :return:
    """
    print(f"args = {pformat(args)}")
    print(f"opt = {pformat(opt)}")

    for i in range(duration):
        time.sleep(1)
        print('tick')
    message = f"pid={os.getpid()}"
    print(message)
    return message

class TimeoutException(Exception):
    """
    to pass data using Exception
    https://stackoverflow.com/questions/16466406/passing-an-object-with-an-exception
    """
    def __init__(self, timeout: Union[int, float]=None,  *args):
        super().__init__(timeout, *args)
        self.timeout = timeout  # used to save partial result

def timeout_func_on_unix(timeout: int, func):
    """
    timeout wrapper. not work well in thread.
    https://stackoverflow.com/questions/492519/timeout-on-a-function-call

    NOT WORKING ON WINDOWS
    https://stackoverflow.com/questions/52779920/why-is-signal-sigalrm-not-working-in-python-on-windows
    in short, windows doesn't implement SIGALRM
    """
    @functools.wraps(func)
    def timed_func(*args, **kwargs):
        def handler(signum, frame):
            raise TimeoutException(timeout=timeout)

        # to check an attribute existence, the reliable way is to instantiate an object and then hasattr()
        # https://stackoverflow.com/questions/44500842/is-there-a-way-to-list-the-attributes-of-a-class-without-instantiating-an-object
        # "because the attributes are dynamic (so called instance attributes)"
        # or use inspect module, but is too complex
        try:
            signal.signal(signal.SIGALRM, handler)
        except AttributeError as e:
            print("Windows doesn't implement signal.SIGALRM")
            raise e
        signal.alarm(timeout)
        return func(*args, **kwargs)
    return timed_func

def timeout_wrapper(func):
    """
    somehow the wrapped function is not pickleable
    :param func:
    :return:
    """
    @functools.wraps(func)
    def wrapper_func(conn: multiprocessing.connection.Connection, *args, **kwargs):
        conn.send(func(*args, **kwargs))
        conn.close()
    return wrapper_func

def timeout_child(conn: multiprocessing.connection.Connection, func, *args, **kwargs):
    """
    wrapper function for timeout_func
    :param conn:
    :param func:
    :param args:
    :param kwargs:
    :return:
    """
    print(f"func={func}")
    conn.send(func(*args, **kwargs))
    conn.close()

def timeout_func(timeout: int, func, *args, **kwargs):
    """
    time out a func. signal.ALRM not working on Windows. therefore this
    https://stackoverflow.com/questions/492519/timeout-on-a-function-call

    so we use multiprocessing.Pipe() to do this
    https://docs.python.org/3.8/library/multiprocessing.html
    use this method because we can
    1. multiprocessing is process-based. process is easier to check and kill after timeout
    2. p.join(timeout) is easier to set timeout
    3. Pipe() is easier to collect return value

    there is decorator using a same method. It has covered a lot of edge conidtions. good place to learn
    https://github.com/bitranox/wrapt_timeout_decorator/blob/master/wrapt_timeout_decorator/wrap_function_multiprocess.py
    """

    parent_conn, child_conn = multiprocessing.Pipe()

    # how to pass args and kwargs
    #   https://stackoverflow.com/questions/38908663/python-multiprocessing-how-to-pass-kwargs-to-function
    p = multiprocessing.Process(target=timeout_child, args=(child_conn, func, *args), kwargs=kwargs)
    p.start()

    # Wait for timeout seconds or until process finishes
    p.join(timeout)

    # If thread is still active
    if p.is_alive():
        message = f"timed out after {timeout}"
        print(message, file=sys.stderr)
        traceback.print_stack()  # default to stderr, set file=sys.stdout for stdout

        # Terminate
        p.terminate()
        p.join(1.0)
        raise TimeoutException(timeout=timeout)
    else:
        result = parent_conn.recv()
        parent_conn.close()
        return result



import types
import copy
def copy_func(f: Callable, global_dict=None, name=None):
    """
    return a function with same code, globals, defaults, closure, and
    name (or provide a new name)

    https://stackoverflow.com/questions/6527633/how-can-i-make-a-deepcopy-of-a-function-in-python/30714299#30714299
    """
    if not name:
        name =f.__name__

    if not global_dict:
        global_dict = globals()
    # https://stackoverflow.com/questions/48629236/how-does-pythons-types-functiontype-create-dynamic-functions
    #fn = types.FunctionType(f.__code__, f.__globals__, name, f.__defaults__, f.__closure__)
    fn = types.FunctionType(f.__code__, global_dict, name, f.__defaults__, f.__closure__)

    #if name:
    #    fn.__name__ = name
    # in case f was given attrs (note this dict is a shallow copy):
    fn.__dict__.update(f.__dict__)
    fn.__qualname__ = name
    return fn

_timeout_child_global_name = None

def main():
    global _timeout_child_global_name

    print('------- test timeout_func_unix(). should work on Unix and fail on windows')
    try:
        sleep_5 = timeout_func_on_unix(5, top_level_sleep_and_tick)
        sleep_5(10)
    except Exception as e:
        print_exception(e)

    print('------- test timeout_func(). should work on both Unix and windows')
    print('------- test timeout_func(). 1. finished before timeout')
    try:
        timeout_func(5, top_level_sleep_and_tick, 2, message ="should finish before timeout")
    except TimeoutException as e:
        print_exception(e)
    print('------- test timeout_func(). 2. timed out')
    try:
        timeout_func(2, top_level_sleep_and_tick, 10, message ="should timeout")
    except TimeoutException as e:
        print_exception(e)

    def local_sleep_and_tick(duration: int, *args, **opt)-> str:
        """
        this is local function:
        https://stackoverflow.com/questions/36994839/i-can-pickle-local-objects-if-i-use-a-derived-class

        """
        print(f"args = {pformat(args)}")
        print(f"opt = {pformat(opt)}")

        for i in range(duration):
            time.sleep(1)
            print('tick')
        message = f"pid={os.getpid()}"
        print(message)
        return message

    print('------- test timeout_func(). 3. local function timed out')
    # this is useless, as it only copies the function name, not the code
    #_timeout_child_global_name = copy.deepcopy(local_sleep_and_tick)

    # this doesn't work either as deepcopy cannot copy functions
    # https://stackoverflow.com/questions/10802002/why-deepcopy-doesnt-create-new-references-to-lambda-function
    #_timeout_child_global_name = copy.deepcopy(local_sleep_and_tick)

    _timeout_child_global_name = copy_func(local_sleep_and_tick, global_dict=globals(), name="_timeout_child_global_name")

    print(_timeout_child_global_name)

    print("run once without timeout")
    _timeout_child_global_name(1, message="1 sec")

    print("run with timeout")
    try:
        # timeout_func(2, local_sleep_and_tick, 10, message="should timeout")
        timeout_func(2, _timeout_child_global_name, 10, message="should timeout")
        '''
        Even used a global name _timeout_child_global_name, the function is still not pickle'able, because
             Note that functions (built-in and user-defined) are pickled by “fully qualified” name reference, 
             not by value. This means that only the function name is pickled, along with the name of the module the 
             function is defined in. Neither the function’s code, nor any of its function attributes are pickled. Thus 
             the defining module must be importable in the unpickling environment, and the module must contain the named 
             object, otherwise an exception will be raised. 
        '''
    except TimeoutException as e:
        print_exception(e)

if __name__ == '__main__':
    main()
