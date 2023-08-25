from glob import glob
import gzip
import os
import re
import stat
import sys
from pprint import pformat, pprint
from typing import Union
from tpsup.modtools import compile_codelist, strings_to_compilable_patterns, load_module
from tpsup.tplog import log_FileFuncLine
from tpsup.util import silence_BrokenPipeError


class TpInput:
    def __init__(self, filename, **opt):
        self.verbose = opt.get('verbose', 0)
        self.need_header = opt.get('need_header', False)
        self.filename = filename
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


def tpglob(file: Union[list, str],  **opt):
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
            files2.extend(globbed)

    return files2


def sorted_files(files: Union[list, str], sort_func, globbed: bool = False, **opt):
    if not globbed:
        files2 = tpglob(files, **opt)
    else:
        files2 = files

    return list(sorted(files2, key=sort_func))


exclude_dirs = set(['.git', '.idea', '__pycache__', '.snapshot'])


def tpfind(paths: Union[list, str],
           FlowExps: list = [],
           FlowDirs: list = [],
           HandleExps: list = [],
           HandleActs: list = [],
           find_print=1,
           find_ls=0,
           find_dump=0,
           **opt):
    verbose = opt.get('verbose', 0)
    if len(FlowExps) != len(FlowDirs):
        raise RuntimeError(
            f'number of FlowExps {len(FlowExps)} not match number of FlowDirs {len(FlowDirs)}')

    if len(HandleExps) != len(HandleActs):
        raise RuntimeError(
            f'number of HandleExps {len(HandleExps)} not match number of HandleActs {len(HandleActs)}')

    CompiledFlowExps = compile_codelist(FlowExps, is_exp=True, verbose=verbose)
    CompiledHandleExps = compile_codelist(HandleExps, is_exp=True)
    CompiledHandleActs = compile_codelist(HandleActs)

    paths2 = tpglob(paths, **opt)

    ret = {}
    ret['error'] = 0

    for p in paths2:
        for root, dirs, fnames in os.walk(p, topdown=True):
            # https://stackoverflow.com/questions/19859840/excluding-directories-in-os-walk
            # key point: use [:] to modify dirs in place
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            isDir = True
            for p in dirs + ['EndOfDirs']+fnames:
                if p == 'EndOfDirs':
                    isDir = False
                    continue

                full_path = os.path.join(root, p)
                if verbose >= 2:
                    print(f'checking "{full_path}"')

                r = {}
                r['full'] = full_path
                r['dir'] = root
                r['short'] = p

                info = os.lstat(full_path)
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
                if isDir:
                    r['type'] = 'dir'
                else:
                    r['type'] = 'file'
                r['fmode'] = stat.filemode(info.st_mode)

                print_p = True
                for i in range(0, len(FlowExps)):
                    compiled = CompiledFlowExps[i]
                    exp = FlowExps[i]
                    direction = FlowDirs[i]
                    if compiled(r):
                        if verbose:
                            log_FileFuncLine(
                                f'Flow exp={exp} matched r={pformat(r)}, direction={direction}')
                        if direction == 'prune':
                            if r['type'] == 'dir':
                                if verbose:
                                    print(f'pruning {r["full"]}')
                                dirs.remove(p)
                                print_p = False
                            # try:
                            #     dirs.remove(p)
                            # except ValueError as e:
                            #     # ValueError: list.remove(x): x not in list
                            #     if verbose:
                            #         log_FileFuncLine(
                            #             f'{e}', file=sys.stderr)
                            continue
                        elif direction == 'exit':
                            return ret

                for i in range(0, len(HandleExps)):
                    exp = HandleExps[i]
                    act = HandleActs[i]
                    compiled = CompiledHandleExps[i]
                    compiled_act = CompiledHandleActs[i]
                    if compiled(r):
                        if verbose:
                            log_FileFuncLine(
                                f'Handle exp={exp} matched r={pformat(r)}, act={act}')
                        compiled_act(r)

                if print_p:
                    if find_dump:
                        print(pformat(r))
                    elif find_ls:
                        print(
                            f'{r["fmode"]} {r["uid"]} {r["gid"]} {r["size"]} {r["mtime"]} {r["full"]}')
                    elif find_print:
                        print(f'{r["full"]}')

    return ret


def sorted_files_by_mtime(files: list, **opt):
    return sorted_files(files, os.path.getmtime, **opt)


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


def main():
    verbose = 1

    file = 'csvtools_test.csv'
    testdir = '/tmp/junkdir'
    file_gz = f'{testdir}/junk.csv.gz'
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
    os.system(f'/bin/rm -fr {testdir}')
    with TpInput(filename=file, MatchPatterns=[',S'], ExcludePatterns=['Stephen'], verbose=verbose) as ti, \
            TpOutput(filename=file_gz) as to:
        for line in ti:
            to.write(line.encode('utf-8'))

    os.system(f'ls -l {file_gz}; zcat {file_gz}; /bin/rm -fr {testdir}')

    from tpsup.exectools import test_lines
    TPSUP = os.environ.get('TPSUP')
    libfiles = f'{TPSUP}/python3/lib/tpsup/*.py'
    p3scripts = f'{TPSUP}/python3/scripts'

    def test_codes():
        sorted_files_by_mtime([libfiles])
        tpfind(TPSUP, FlowExps=['not(r["full"].endswith("profile.d"))'],
               FlowDirs=['prune'], )
        tpfind(p3scripts, FlowExps=['r["size"] > 2000'],
               FlowDirs=['exit'])

        stat.filemode(0o100644)
        un_filemode('-rw-r--r--')
        oct(un_filemode('-rw-r--r--'))
        oct(un_filemode('-rw-r--r--') & 0o777)
        0o100644
        oct(33188)

    test_lines(test_codes, source_globals=globals(), source_locals=locals())


if __name__ == '__main__':
    main()
