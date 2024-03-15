from glob import glob
import gzip
import os
import re
import stat
import sys
from pprint import pformat, pprint
import time
import types
from typing import Union
from tpsup.cmdtools import run_cmd
from tpsup.modtools import compile_codelist, strings_to_compilable_patterns, load_module
from tpsup.logbasic import log_FileFuncLine
from tpsup.utilbasic import silence_BrokenPipeError


class TpInput:
    def __init__(self, filename, **opt):
        self.verbose = opt.get('verbose', 0)
        self.need_header = opt.get('need_header', False)
        self.filename = filename.replace('\\', '/')
        self.need_close_fh = False
        self.fh = None

        source_list = ['import re']

        for attr in ['MatchPatterns', 'ExcludePatterns']:
            # need to convert pattern string into bytes-like object as we read the csv as binary data
            strings = opt.get(attr, [])
            source_list.append(strings_to_compilable_patterns(strings, attr))

        source = '\n\n'.join(source_list)

        if self.verbose >= 2:
            sys.stderr.write(f'source code = \n{source}\n')

        pattern_filter = load_module(source)

        self.match_patterns = pattern_filter.MatchPatterns
        self.exclude_patterns = pattern_filter.ExcludePatterns

        self.skip = opt.get('skip', 0)

    def open(self):
        if self.filename == '-':
            self.fh = sys.stdin
        else:
            self.need_close_fh = True
            # the unicode-sandwich design pattern
            if self.filename.endswith('.gz'):
                # in /usr/lib/python/3.6/gzip.py, open()
                # if "t" in mode:
                #     if "b" in mode:
                #         raise ValueError("Invalid mode: %r" % (mode,))
                # else:
                #     if encoding is not None:
                #         raise ValueError("Argument 'encoding' not supported in binary mode")
                #     if errors is not None:
                #         raise ValueError("Argument 'errors' not supported in binary mode")
                #     if newline is not None:
                #         raise ValueError("Argument 'newline' not supported in binary mode")

                self.fh = gzip.open(self.filename, 'rt',
                                    encoding='utf-8', newline='')
            else:
                self.fh = open(self.filename, 'r',
                               encoding='utf-8', newline='')

        for count in range(0, self.skip):
            try:
                next(self.fh)
            except StopIteration:
                break
        return self

    def readline(self):
        line_number = 0

        # UnicodeDecodeError: 'utf-8' codec can't decode byte 0xc1 in position 24:
        #     invalid start byte
        try:
            for line in self.fh:
                line_number += 1

                if line_number == 1 and self.need_header:
                    # csv module needs the header line
                    yield line
                    continue

                matched = 1
                for compiled in self.match_patterns:
                    # if not compiled.match(line):
                    if not compiled.search(line):
                        matched = 0
                        break

                if not matched:
                    continue

                excluded = 0

                for compiled in self.exclude_patterns:
                    if compiled.search(line):
                        excluded = 1
                        break
                if excluded:
                    continue

                # print(f'iamhere {line}')
                yield line
        except UnicodeDecodeError as e:
            print(f'{e} in {self.filename}', file=sys.stderr)
            return
        return

    def close(self):
        if self.need_close_fh:
            self.fh.close()
        self.fh = None
        self.need_close_fh = False

    def closed(self) -> bool:
        return not self.fh

    def __iter__(self):
        return self.readline()

    def __enter__(self):
        return self.open()

    def __exit__(self, exec_type, exc_value, traceback):
        self.close()


class TpOutput:
    def __init__(self, filename, **opt):
        self.verbose = opt.get('verbose', 0)
        self.filename = filename
        self.need_close_fh = False
        self.fh = None

    def __enter__(self):
        if self.filename == '-':
            self.fh = sys.stdout
            # overwrite a standard function
            self.fh.write = silence_BrokenPipeError(self.fh.write)
        else:
            os.makedirs(os.path.dirname(self.filename), exist_ok=True)
            self.need_close_fh = True
            if self.filename.endswith('.gz'):
                self.fh = gzip.open(self.filename, 'wb')
            else:
                self.fh = open(self.filename, 'w', encoding='utf-8')
        return self.fh

    def close(self):
        if self.need_close_fh:
            self.fh.close()
        self.fh = None
        self.need_close_fh = False

    def closed(self) -> bool:
        return not self.fh

    def __exit__(self, exec_type, exc_value, traceback):
        self.close()


def tpglob(file: Union[list, str],
           sort_name=None,
           sort_func=None,
           reverse=False,
           **opt):
    if isinstance(file, str):
        files = file.split()
    elif isinstance(file, list):
        files = file
    else:
        raise RuntimeError(
            f'unsupported type {type(file)} of file={pformat(file)}\nIt must be a list or a string')

    files2 = []
    for f in files:
        if f == '-':
            # this is stdin
            files2.append(f)
        else:
            globbed = glob(f)
            if not globbed:
                log_FileFuncLine(f'{f} not found', file=sys.stderr)
                continue
            posixed = [x.replace('\\', '/') for x in globbed]
            files2.extend(posixed)

    if sort_name or sort_func:
        return sort_files(files2,
                          sort_name=sort_name,
                          sort_func=sort_func,
                          reverse=reverse,
                          globbed=True,  # this is to avoid infinite loop
                          **opt)
    else:
        return files2 if not reverse else files2[::-1]


mtime_by_file = {}


def get_mtime(file: str, **opt):
    global mtime_by_file

    if file in mtime_by_file:
        return mtime_by_file[file]

    mtime = os.path.getmtime(file)
    mtime_by_file[file] = mtime
    return mtime


size_by_file = {}


def get_size(file: str, **opt):
    global size_by_file

    if file in size_by_file:
        return size_by_file[file]

    size = os.path.getsize(file)
    size_by_file[file] = size
    return size


def sort_files(files: Union[list, str],
               sort_name: str = None,
               sort_func=None,
               reverse=False,
               globbed: bool = False,  # sort_files() uses this to avoid infinite loop
               **opt):
    if not globbed:
        files2 = tpglob(files, **opt)
    else:
        files2 = files

    # python's sorted() is different from perl's sort()
    #    sorted() takes a key arg, which converts a list item to a comparable object
    #    sort() takes a cmp arg, which compares 2 list items
    # therefore, their sort_func are different.
    if not sort_func:
        if sort_name:
            if sort_name == 'mtime':
                sort_func = get_mtime
            elif sort_name == 'name':
                pass
            elif sort_name == 'size':
                sort_func = get_size
            else:
                raise RuntimeError(f'unknown sort_name={sort_name}')

    if sort_func or sort_name:
        if sort_func:
            return sorted(files2, key=sort_func, reverse=reverse)
        else:
            return sorted(files2, reverse=reverse)
    else:
        return files2


def get_latest_files(files: list, **opt):
    return sort_files(files, sort_name='mtime', reverse=True, **opt)


exclude_dirs = set(['.', '..', '-', '.git', '.idea',
                   '__pycache__', '.snapshot', '.vscode'])


def tpfind(paths: Union[list, str],
           MatchExps: list = [],
           FlowExps: list = [],
           FlowDirs: list = [],
           HandleExps: list = [],
           HandleActs: list = [],
           no_print: bool = False,
           find_print: bool = False,
           find_ls: bool = False,
           find_dump: bool = False,
           MaxCount: int = None,
           MaxDepth: int = None,
           **opt):

    # verbose will be passed to downstream functions, therefore, it stays in **opt
    verbose = opt.get('verbose', 0)

    import platform
    if platform.system().lower().startswith("lin"):
        import pwd
        import grp
        is_linux = True
    else:
        is_linux = False

    if len(FlowExps) != len(FlowDirs):
        raise RuntimeError(
            f'number of FlowExps {len(FlowExps)} not match number of FlowDirs {len(FlowDirs)}')

    if len(HandleExps) != len(HandleActs):
        raise RuntimeError(
            f'number of HandleExps {len(HandleExps)} not match number of HandleActs {len(HandleActs)}')

    # no_print is used to suppress printing the path, for example,
    # when another function calls tpfind() to get a list of files.
    if not no_print:
        # find_print is the default print method
        find_print = find_print or not (
            find_ls or find_dump or FlowExps or HandleExps)

    mod_name = 'tmp_mod'
    mod_source = '''
import os
import re
import tpsup.filetools


r = None
# readline_gen = None

def export_r(r2):
    global r
    # global r, readline_gen
    r = r2
    
    # # reset readline_gen so that we can start a new generator
    # readline_gen = None

# def readline(**opt):
#     global r, readline_gen
#     if not readline_gen:
#         def gen(**opt):
#             with tpsup.filetools.TpInput(filename=r['path'], **opt) as tf:
#                 for line in tf:
#                     yield line
#         readline_gen = gen(**opt) 
#         # mention gen() with '()' to call it - init it.


#     return next(readline_gen) 
#     # mention readline_gen without "()" because we don't call the generator here.
#     # the generator is already running.

def getline(**opt):
    # this is mimic perl-version's getline()
    global r
    lines = []
    if 'count' in opt:
        count = opt['count']
        ret_type = 'list'
    else:
        count = 1
        ret_type = 'str'
    i = 0
    with tpsup.filetools.TpInput(filename=r['path'], **opt) as tf:
        for line in tf:
            lines.append(line)
            i += 1
            if i >= count:
                break
    if ret_type == 'str':
        return lines[0]
    else:
        return lines

'''
    mod = sys.modules.setdefault(mod_name, types.ModuleType(mod_name))
    mod_code = compile(mod_source, mod_name, 'exec')
    exec(mod_code, mod.__dict__)

    # keep all functions in 1 module so that we only need to export 'r' once
    CompiledMatchExps = compile_codelist(
        MatchExps, existing_module=mod, is_exp=True)
    CompiledFlowExps = compile_codelist(
        FlowExps, existing_module=mod, is_exp=True, verbose=verbose)
    CompiledHandleExps = compile_codelist(
        HandleExps, existing_module=mod, is_exp=True)
    CompiledHandleActs = compile_codelist(HandleActs, existing_module=mod,)

    # either of the following 2 lines works.
    # the 2nd line will not trigger pylint warning.

    # export_r = mod.export_r
    export_r = getattr(mod, 'export_r')

    ret = {
        'error': 0,
        'hashes': [],
        'count': 0,
    }

    now = time.time()

    #############################################################
    # begin - function inside function
    # we use function inside function to avoid passing too many parameters.
    def print_path(r: dict):
        if find_dump:
            print(pformat(r))
        elif find_ls:
            print(
                f'{r["fmode"]} {r["owner"]:7} {r["group"]:7} {r["size"]:7} {r["mtimel"]} {r["path"]}')
        elif find_print:
            print(f'{r["path"]}')

    def process_node(full_path: str = None, **opt):
        # 'r' is the node info, for expression matching.
        # 'result' is the return value of this function, mainly for flow control.
        r = {}
        result = {}

        r['path'] = full_path
        r['short'] = os.path.basename(full_path)

        if os.path.isdir(full_path):
            r['type'] = 'dir'
        elif os.path.islink(full_path):
            r['type'] = 'link'
        else:
            r['type'] = 'file'

        info = os.lstat(r['path'])
        r['dev'] = info.st_dev
        r['ino'] = info.st_ino
        r['mode'] = info.st_mode
        r['nlink'] = info.st_nlink
        r['uid'] = info.st_uid
        r['gid'] = info.st_gid
        r['size'] = info.st_size
        r['atime'] = info.st_atime
        r['mtime'] = info.st_mtime
        r['ctime'] = info.st_ctime

        r['now'] = now
        r['fmode'] = stat.filemode(info.st_mode)

        r['atimel'] = time.strftime(
            '%Y%m%d-%H:%M:%S', time.localtime(r['atime']))
        r['ctimel'] = time.strftime(
            '%Y%m%d-%H:%M:%S', time.localtime(r['ctime']))
        r['mtimel'] = time.strftime(
            '%Y%m%d-%H:%M:%S', time.localtime(r['mtime']))

        if is_linux:
            # https://stackoverflow.com/questions/7770034/in-python-and-linux
            # -how-to-get-given-users-id
            # https://docs.python.org/2/1ibrary/pwd.html
            _pwd = pwd.getpwuid(r['uid'])
            r['owner'] = _pwd.pw_name

            # https://docs.python.org/2/library/grp.html#module-grp
            _grp = grp.getgrgid(r['gid'])
            r['group'] = _grp.gr_name
        else:
            r['owner'] = r['uid']
            r['group'] = r['gid']

        # export r into the module, so that functions in the module can access it.
        export_r(r)

        for i in range(0, len(FlowExps)):
            compiled = CompiledFlowExps[i]
            exp = FlowExps[i]
            direction = FlowDirs[i]

            try:
                passed = compiled()
            except Exception as e:
                print(e)
                passed = False
            if passed:
                if verbose:
                    log_FileFuncLine(
                        f'Flow exp={exp} matched r={pformat(r)}, direction={direction}')
                if direction == 'prune':
                    if verbose:
                        print(f'pruning {r["path"]}')
                    result['direction'] = 'prune'
                    continue
                elif direction == 'exit':
                    result['direction'] = 'exit'
                    return result

        count_path = True

        if HandleExps:
            count_path = False
        for i in range(0, len(HandleExps)):
            exp = HandleExps[i]
            act = HandleActs[i]
            compiled = CompiledHandleExps[i]
            compiled_act = CompiledHandleActs[i]
            try:
                if compiled():
                    count_path = True
                    if verbose:
                        log_FileFuncLine(
                            f'Handle exp={exp} matched r={pformat(r)}, act={act}')
                    compiled_act()
            except Exception as e:
                print(e)

        if MatchExps:
            count_path = False
            # MatchExps doesn't affect flow control;
            # it only affects whether to count or print the path
            all_matched = True
            for i in range(0, len(MatchExps)):
                exp = MatchExps[i]
                compiled = CompiledMatchExps[i]

                try:
                    passed = compiled()
                except Exception as e:
                    print(e)
                    passed = False

                if not passed:
                    if verbose >= 2:
                        log_FileFuncLine(
                            f'Match exp={exp} failed r={pformat(r)}')
                    all_matched = False
                    break
            if not all_matched:
                return result
            else:
                count_path = True

        if count_path:
            ret['hashes'].append(r)
            ret['count'] += 1
            print_path(r)
        return result

    # end - function inside function
    #############################################################

    # the following mimic perl's tpfind()
    globbed_paths = tpglob(paths, **opt)

    pathLevels = []
    for path in globbed_paths:
        pathLevel = [path, 0]
        pathLevels.append(pathLevel)

    seen = {}

    while pathLevels:
        if MaxCount is not None:
            if ret['count'] >= MaxCount:
                break

        pathLevel = pathLevels.pop(0)
        path, level = pathLevel

        if path == '-':
            # this is stdin. skip it.
            # we could come here when tpfind() is called by tpgrep() which
            # can take stdin as input.
            continue

        result = process_node(full_path=path, **opt)
        if direction := result.get('direction', None):
            if direction == 'exit':
                return ret
            elif direction == 'prune':
                continue

        if MaxDepth is not None:
            if level >= MaxDepth:
                continue

        if os.path.isdir(path):
            shorts = os.listdir(path)
            for short in shorts:
                if short in exclude_dirs:
                    continue

                path2 = f'{path}/{short}'
                if path2 in seen:
                    continue
                seen[path2] = 1

                pathLevel = [path2, level + 1]
                pathLevels.append(pathLevel)

    return ret


def un_filemode(mode_str):
    '''
    this is the inverse function of stat.filemode().

    stat.filemode() changes 0o644 to '-rw-r--r--'

    https://stackoverflow.com/questions/46099181
    convert '-rw-r--r--' to 0o644
    '''
    mode = 0
    for char, table in zip(mode_str, stat._filemode_table):
        for bit, bitchar in table:
            if char == bitchar:
                mode |= bit
                break
    return mode


def ls(files: Union[list, str], ls_args: str = "", print_ls=1, **opt):
    verbose = opt.get('verbose', 0)
    files2 = tpglob(files, **opt)

    if not files2:
        print(f'no file found for {files}')
        return {
            'rc': 1,
            'stdout': None,
            'stderr': f'no file found for {files}',
        }

    # wrap each file with double quotes so that we can handle file names with spaces
    files_string = '"' + '" "'.join(files2) + '"'

    cmd = f'ls {ls_args} {files_string}'  # we will run it with bash so that it works in windows

    if verbose > 1:
        print(f'cmd = {cmd}')

    # run with bash so that it works in windows
    result = run_cmd(cmd, is_bash=True, print_output=print_ls)

    return result


def ls_l(files, **opt):
    return ls(files, **opt, ls_args='-l')


def main():
    verbose = 1

    import tpsup.tmptools
    tmpdir = tpsup.tmptools.get_dailydir()

    file = 'csvtools_test.csv'
    file_gz = f'{tmpdir}/junk.csv.gz'
    print('test1')

    with TpInput(filename=file, ExcludePatterns=['Smith'], verbose=verbose) as tf:
        for line in tf:
            print(line, end='')

    print('test2')
    import csv
    with TpInput(filename=file, MatchPatterns=[',S'], ExcludePatterns=['Stephen'], verbose=verbose) as tf:
        reader = csv.DictReader(tf)
        headers = reader.fieldnames
        print(headers)
        for row in reader:
            pprint(row)

    print('test3')
    # os.system(f'/bin/rm -fr {testdir}')
    run_cmd(f"/bin/rm -fr '{tmpdir}'", is_bash=True, print_output=verbose)
    with TpInput(filename=file, MatchPatterns=[',S'], ExcludePatterns=['Stephen'], verbose=verbose) as ti, \
            TpOutput(filename=file_gz) as to:
        for line in ti:
            print(line, end='')
            to.write(line.encode('utf-8'))

    # os.system(f'ls -l {file_gz}; zcat {file_gz}; /bin/rm -fr {testdir}')
    run_cmd(f"ls -l '{file_gz}'; zcat '{file_gz}'; /bin/rm -fr '{tmpdir}'", is_bash=True, print_output=verbose)

    from tpsup.testtools import test_lines
    TPSUP = os.environ.get('TPSUP')
    libfiles = f'{TPSUP}/python3/lib/tpsup/*tools.py'
    p3scripts = f'{TPSUP}/python3/scripts'
    searchfiles = f'{TPSUP}/python3/lib/tpsup/searchtools_test*.txt'

    def test_codes():
        sort_files([libfiles], sort_name='mtime')
        tpglob(searchfiles)
        tpglob(searchfiles, sort_name='mtime')
        get_latest_files([libfiles])[:2]  # get the latest 2 files
        tpfind(TPSUP, FlowExps=['r["short"] in ["scripts", "lib", "python3", "cmd_exe"]'],
               FlowDirs=['prune'],
               MaxCount=5)

        tpfind(p3scripts, FlowExps=['r["size"] > 2000'],
               FlowDirs=['exit'],
               find_ls=1,
               MaxCount=5)
        tpfind(p3scripts,
               HandleExps=[
                   # file mode in cygwin and git bash is not handled correctly in python.
                   'r["type"] == "file" and r["size"] > 0 and getline().startswith("#!") and (r["mode"] & 0o755) != 0o755'
                   #    'r["type"] == "file" and r["size"] > 0',
               ],
               HandleActs=[
                   '''print('------');print(getline(count=10));os.system(f"ls -l {r['path']}")'''],
               MaxCount=5,
               )

        stat.filemode(0o100644)
        un_filemode('-rw-r--r--')
        oct(un_filemode('-rw-r--r--'))
        oct(un_filemode('-rw-r--r--') & 0o777)
        0o100644
        oct(33188)
        ls_l([f'{p3scripts}/ptgrep*'])

    test_lines(test_codes, source_globals=globals(), source_locals=locals())


if __name__ == '__main__':
    main()
