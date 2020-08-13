import functools
import multiprocessing
import multiprocessing.connection
import os
import signal
import time
import traceback
from pprint import pformat
from typing import Union, Callable
import types


from tpsup.util import print_exception, tplog, tplog_exception

# multiprocessing.set_start_method('spawn')

class TimeoutException(Exception):
    """
    to pass data using Exception
    https://stackoverflow.com/questions/16466406/passing-an-object-with-an-exception
    """

    def __init__(self, timeout: Union[int, float] = None, child_pid = None, *args):
        super().__init__(timeout, *args)
        self.timeout = timeout  # used to save partial result
        self.child_pid = child_pid  # pid of the child process

def timeout_func_on_unix(timeout: int, func, *args, **kwargs):
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


def timeout_child(conn: multiprocessing.connection.Connection, func: types.FunctionType, *args, **kwargs):
    """
    wrapper function for timeout_func
    :param conn:
    :param func:
    :param args:
    :param kwargs:
    :return:
    """
    verbose = kwargs.get('verbose', 0)
    if verbose:
        tplog(f"func={func}")
    if not func:
        # https://stackoverflow.com/questions/43369648/cant-get-attribute-function-inner-on-module-mp-main-from-e-python
        # when the multiprocessing library copies your main module, it won't run it as the __main__ script and
        # therefore anything defined inside the if __name__ == '__main__' is not defined in the child process
        # namespace. Hence, the AttributeError
        message = f"both func={func} is not initialized. note: func cannot be defined in __main__"
        tb = pformat(traceback.format_stack()) # outside exception use format_stack()
        conn.send(RuntimeError(f"{message}\n{tb}"))
    else:
        result = None
        try:
            result = func(*args, **kwargs)
            conn.send(result)
        except Exception as e:
            tb = pformat(traceback.format_exc()) # within exception use format_exc()
            conn.send(RuntimeError(f"child process exception, pid={os.getpid()}\n{tb}"))
    conn.close()

# typing.Callable vs types.FunctionType
# https://stackoverflow.com/questions/55873205/using-type-hint-annotation-using-types-functiontype-vs-typing-callable
#
# The types module predates PEP 484 annotations and was created mostly to make runtime introspection
# of objects easier. For example, to determine if some value is a function, you can run isinstance(my_var,
# types.FunctionType).
#
# The typing module contains type hints that are specifically intended to assist static analysis tools such
# as mypy. For example, suppose you want to indicate that a parameter must be a function that accepts two
# ints and returns a str. You can do so like this:
#
# type hint use typing.Callable is better then types.FunctionType
# def timeout_func(timeout: int, func: types.FunctionType, *args, **kwargs):
def timeout_func(timeout: int, func: Callable, *args, **kwargs):
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

    # multiprocessing cannot run child with function defined in __main__
    #   https://stackoverflow.com/questions/43369648/cant-get-attribute-function-inner-on-module-mp-main-from-e-python
    #   when the multiprocessing library copies your main module, it won't run it as the __main__ script
    #   and therefore anything defined inside the if __name__ == '__main__' is not defined in the child
    #   process namespace. Hence, the AttributeError
    # I tried to reload module or delay import module to work around this. neither worked.
    # re-import failed to work around
    #   importlib.reload(multiprocessing)
    #   importlib.reload(multiprocessing.connection)
    # delayed import failed to work around
    #   import multiprocessing
    #   import multiprocessing.connection

    # the parent process can always see the process defined in __main__
    #   tplog(getattr(sys.modules['__mp_main__'], 'local_sleep_and_tick'))

    parent_conn, child_conn = multiprocessing.Pipe(duplex=False)

    # how to pass args and kwargs
    #   https://stackoverflow.com/questions/38908663/python-multiprocessing-how-to-pass-kwargs-to-function
    # p = multiprocessing.Process(target=timeout_child, args=(child_conn, func, *args), kwargs=kwargs)
    p = multiprocessing.Process(target=timeout_child, args=(child_conn, func, *args), kwargs=kwargs)

    # kill child after parent exits
    # https://stackoverflow.com/questions/25542110/kill-child-process-if-parent-is-killed-in-python
    p.daemon = True

    p.start()

    # Wait for timeout seconds or until process finishes
    p.join(timeout)

    # If thread is still active
    if p.is_alive():
        message = f"timed out after {timeout} second(s), terminating pid={p.pid}"
        tplog(message)
        traceback.print_stack()  # default to stderr, set file=sys.stdout for stdout

        # Terminate
        p.terminate()
        p.join(0.5)
        parent_conn.close()
        raise TimeoutException(timeout=timeout, child_pid=p.pid)
    else:
        result = None
        if parent_conn.poll(0.1):
            # recv() is a blocked call, therefore, poll() first
            result = parent_conn.recv()
            parent_conn.close()
            if isinstance(result, Exception):
                raise result
            else:
                # child finished and returned anything
                return result
        else:
            # child finished but didn't return anything
            parent_conn.close()

def module_sleep_and_tick(duration: int, *args, **opt) -> str:
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

def test_child_exception():
    time.sleep(1)
    raise RuntimeError("test exception")

def main():
    print('------- test timeout_func_unix(). should work on Unix and fail on windows')
    try:
        sleep_5 = timeout_func_on_unix(2, module_sleep_and_tick, 3)
        sleep_5(10)
    except Exception as e:
        # error on Windows
        # AttributeError: module 'signal' has no attribute 'SIGALRM'
        print_exception(e)

    def main_sleep_and_tick(duration: int, *args, **opt) -> str:
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

    b = main_sleep_and_tick
    print(f"type={type(module_sleep_and_tick)}")
    print('------- test timeout_func(). with function defined in module, should work but will time out')
    try:
        result = timeout_func(2, module_sleep_and_tick, 10, message="should timeout")
        tplog(f"result={pformat(result)}")
    except TimeoutException as e:
        tplog_exception(e)
        tplog("got expected exception\n\n")

    print('------- test timeout_func(). with function defined in main, may work on unix but should fail on windows '
          'with pickle error')
    try:
        result = timeout_func(2, main_sleep_and_tick, 10, message="should timeout")
        tplog(f"result={pformat(result)}")
    except AttributeError as e:
        # AttributeError: Can't pickle local object 'main.<locals>.main_sleep_and_tick'
        tplog_exception(e)
        tplog("got expected exception\n\n")

    print('\n------- test timeout_func(). child will raise exception')
    try:
        result = timeout_func(3, test_child_exception)
        tplog(f"result={pformat(result)}")
    except TimeoutException as e:
        tplog_exception(e)
        tplog("got expected exception\n\n")

if __name__ == '__main__':
    main()
