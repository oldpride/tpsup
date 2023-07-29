import inspect
import logging
import os
import pprint

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


def get_FileFuncLine():
    frame = inspect.stack()[2]
    return f"{frame.filename}:{frame.function}:{frame.lineno}"


def log_FileFuncLine(msg: str, **opt):
    print(f'{get_FileFuncLine()}: {msg}', **opt)


def log_FileFuncLineObj(obj_name, obj, **opt):
    msg = pprint.pformat(obj)
    # if msg is multi-line, add a new line in between
    if '\n' in msg:
        print(f'{get_FileFuncLine()}: {obj_name}=\n{msg}')
    else:
        print(f'{get_FileFuncLine()}: {obj_name}= {msg}')


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
        import tpsup.cmdtools
        tpsup.cmdtools.ls_l(f'{file}*')


def main():
    print()
    print("----------------------------------------")
    print("test log_FileFuncLine")
    log_FileFuncLine("This is a test")

    print()
    print("----------------------------------------")
    print("test logger")
    logger = get_logger()
    logger.debug("This is a debug log")
    logger.info("This is an info log")
    logger.critical("This is critical")
    logger.error("An error occurred")

    logger.setLevel(level='WARN')
    logger.info("I should not see this line")

    # logging.basicConfig(level="DEBUG")
    logger2 = get_logger('new')
    logger2.info("I should see this line")

    print()
    print("-----------------------------------------")
    print("test rotate_log")
    # create a file with 100 bytes
    import tpsup.tptmp
    tmpdir = tpsup.tptmp.get_dailydir()
    testfile = f"{tmpdir}/test.log"
    size = 100

    for i in range(3):
        print(f'round {i}')
        import tpsup.cmdtools
        print('starting point')
        tpsup.cmdtools.ls_l(f'{testfile}*')
        with open(testfile, "wb") as fh:
            fh.seek(size-1)
            fh.write(b'\0')
        print('after creating the file')
        tpsup.cmdtools.ls_l(f'{testfile}*')
        print('rotating...')
        rotate_log(testfile, count=i, size=99, verbose=2)

    print()
    print("-----------------------------------------")
    print("test log_FileFuncLineObj")
    test_obj = {'a': 1, 'b': 2}
    log_FileFuncLineObj('test_obj', test_obj)


if __name__ == '__main__':
    main()
