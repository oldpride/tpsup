import inspect
import io
import logging
import os
import pprint
import sys
from time import localtime, strftime, gmtime
import traceback

from tpsup.exectools import exec_into_globals


default = {
    # %(msecs)03d, pad with 0
    'format': '%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(funcName)s:%(lineno)d] %(message)s',
    'datefmt': '%Y%m%d:%H:%M:%S',
    'level': 'INFO',
    'filename': None
}


def get_logger(name: str = None, **kwargs):
    if not name:
        name = __name__
    setting = dict(default)
    setting.update(**kwargs)
    logging.basicConfig(**setting)
    # once you get the logger, you cannot change it. but you can get a new one with new name
    return logging.getLogger(name)


def get_stack(level: int = 2):
    caller = inspect.stack()[level]
    return f"{os.path.basename(caller.filename)},{caller.lineno},{caller.function}()"


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
        print("{0}: {1}".format(type(e).__name__,
              ";".join(e.args)), file=file, **opt)

    if sio:
        string = sio.getvalue()
        sio.close()
        return string


def get_exception_string(e: Exception, **opt):
    return print_exception(e, file=str)


def tplog_exception(e: Exception, **opt):
    tplog(print_exception(e, file=str), **opt)


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


def rotate_log(file: str, size: int = 1024*1024, count: int = 1, **opt):
    # rotate the log file if it is bigger than the size.
    # save the backup in the same dir with a .number extension.

    verbose = opt.get('verbose', 0)

    # check the file size
    if not os.path.isfile(file):
        if verbose > 1:
            print(f'{file} is not a file')
        return

    if (size2 := os.path.getsize(file)) < size:
        if verbose > 1:
            print(f'{file} size {size2} is smaller than {size}. no need to rotate')
        return

    # rotate the file
    # remove the last backup
    # check if the backup exists
    if os.path.isfile(f'{file}.{count}'):
        if verbose > 1:
            print(f'remove {file}.{count}')
        os.remove(f'{file}.{count}')

    for i in range(count, 0, -1):
        # move the backup to the next one
        if i == 1:
            old_file = f"{file}"
        else:
            old_file = f"{file}.{i-1}"

        if os.path.isfile(old_file):
            if verbose > 1:
                print(f'rename {old_file} to {file}.{i}')
            os.rename(f'{old_file}', f'{file}.{i}')

    if verbose > 1:
        print('after rotating')
        import tpsup.filetools
        tpsup.filetools.ls_l(f'{file}*')


def get_logs(logs, LogLastCount=None, **opt):
    verbose = opt.get('verbose', 1)

    log_patterns = []
    if isinstance(logs, str):
        log_patterns = [logs]
    elif isinstance(logs, list):
        log_patterns = logs
    else:
        raise RuntimeError(f"logs={logs} is not a string or a list")

    from tpsup.filetools import ls

    all_logs = []
    for lp in log_patterns:
        # cmd = f"/bin/ls -1dtr {lp}"
        # if verbose:
        #     print(f"cmd={cmd}")
        # lines = os.popen(cmd).read().splitlines()

        result = ls(lp, ls_args="-1dtr", print=0)
        lines = result['stdout'].splitlines()
        all_logs.extend(lines)

    if LogLastCount is None:
        return all_logs
    else:
        if LogLastCount >= len(all_logs):
            return all_logs
        else:
            return all_logs[-LogLastCount:]


# # because globals() and locals() are all relative to batch.py, therefore
# # we cannot move exec_simple() to tpsup.exectools.
# def exec_simple(source, **opt):
#     return exec_into_globals(source, globals(), locals(), **opt)


def get_logname_cfg(cfg_file: str, **opt):
    verbose = opt.get('verbose', 1)

    if not os.path.isfile(cfg_file):
        raise RuntimeError(f"{cfg_file} not found")

    if not os.access(cfg_file, os.R_OK):
        raise RuntimeError(f"{cfg_file} not readable")

    yyyymmdd = opt.get('yyyymmdd', None)
    if yyyymmdd is None:
        yyyymmdd = strftime("%Y%m%d", localtime())

    yy2, yy, mm, dd = yyyymmdd[:2], yyyymmdd[2:4], yyyymmdd[4:6], yyyymmdd[6:8]
    yyyy = f"{yy2}{yy}"

    from tpsup.utilbasic import resolve_scalar_var_in_string
    from tpsup.envtools import get_user
    user = get_user()

    with open(cfg_file, "r") as fh:
        cfg_string = fh.read()

    string2 = resolve_scalar_var_in_string(cfg_string, {yyyymmdd: yyyymmdd, user: user})

    our_logname_cfg = {}
    exec_into_globals(string2, source_filename=cfg_file)
    if verbose:
        print(f"our_logname_cfg={our_logname_cfg}")

    return our_logname_cfg


def get_logs_by_cfg(cfg_file: str, cfg_key: str, yyyymmdd=None, BackwardDays=0, **opt):
    verbose = opt.get('verbose', 0)

    if yyyymmdd is None:
        yyyymmdd = strftime("%Y%m%d", localtime())

    yy2, yy, mm, dd = yyyymmdd[:2], yyyymmdd[2:4], yyyymmdd[4:6], yyyymmdd[6:8]
    yyyy = f"{yy2}{yy}"

    days = [yyyymmdd]
    if BackwardDays:
        for i in range(1, BackwardDays+1):
            day = strftime("%Y%m%d", localtime(strftime("%s", localtime()) - i*86400))
            days.append(day)

    logs = []
    seen = set()
    for day in days:
        all_cfg = get_logname_cfg(cfg_file, **opt, yyyymmdd=day)
        if verbose:
            print(f"all_cfg = {all_cfg}")

        cfg = all_cfg[cfg_key]

        if cfg is None:
            raise RuntimeError(f"'{cfg_key}' is not defined in {cfg_file}")

        patterns = []
        pattern_keys = []
        if day == strftime("%Y%m%d", localtime()):
            pattern_keys = ['yyyymmdd_pattern', 'today_pattern']
        else:
            pattern_keys = ['yyyymmdd_pattern']

        for k in pattern_keys:
            pattern = cfg.get(k)
            if pattern is not None:
                patterns.append(pattern)

        logs2 = get_logs(patterns, **opt, yyyymmdd=day)

        for log in logs2:
            if log not in seen:
                logs.append(log)
                seen.add(log)

    return logs


def main():
    logger = get_logger()
    # logging.basicConfig(level="DEBUG")
    logger2 = get_logger('new')

    def test_codes():
        logger.debug("This is a debug log")
        logger.info("This is an info log")
        logger.critical("This is critical")
        logger.error("An error occurred")

        logger.setLevel(level='WARN')
        logger.info("I should not see this line")
        logger2.info("I should see this line")

        tplog("hello world")
        tplog("hello world", prefix="time")

    from tpsup.testtools import test_lines
    test_lines(test_codes, source_globals=globals(), source_locals=locals())

    print("\n------ test print_exception")
    try:
        raise RuntimeError("test exception")
    except Exception as e:
        print_exception(e)
        tplog(print_exception(e, file=str))

    print()
    print("-----------------------------------------")
    print("test rotate_log")
    # create a file with 100 bytes
    import tpsup.tmptools
    tmpdir = tpsup.tmptools.get_dailydir()
    testfile = f"{tmpdir}/test.log"
    size = 100

    for i in range(3):
        print(f'round {i}')
        import tpsup.filetools
        print('starting point')
        tpsup.filetools.ls_l(f'{testfile}*')
        with open(testfile, "wb") as fh:
            fh.seek(size-1)
            fh.write(b'\0')
        print('after creating the file')
        tpsup.filetools.ls_l(f'{testfile}*')
        print('rotating...')
        rotate_log(testfile, count=i, size=99, verbose=2)


if __name__ == '__main__':
    main()
