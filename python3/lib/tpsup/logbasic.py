import inspect
import os
import pprint

# separated this from logtools.py to avoid circular import, or dependency loop


def get_FileFuncLine():
    frame = inspect.stack()[2]
    return f"{os.path.basename(frame.filename)}:{frame.function}:{frame.lineno}"


def log_FileFuncLine(msg: str = None, **opt):
    if msg is None:
        string = ""
    else:
        string = f": {msg}"
    print(f'{get_FileFuncLine()}{string}', **opt)


def log_FileFuncLineObj(obj_name, obj, **opt):
    msg = pprint.pformat(obj)
    # if msg is multi-line, add a new line in between
    if '\n' in msg:
        print(f'{get_FileFuncLine()}: {obj_name}=\n{msg}')
    else:
        print(f'{get_FileFuncLine()}: {obj_name}= {msg}')


def main():
    test_obj = {'a': 1, 'b': 2}

    def test_codes():
        log_FileFuncLine("This is a test")

        log_FileFuncLineObj('test_obj', test_obj)

    from tpsup.exectools import test_lines
    test_lines(test_codes, source_globals=globals(), source_locals=locals())


if __name__ == '__main__':
    main()
