#!/usr/bin/env python

import argparse
import sys
import textwrap
from pprint import pformat
from inspect import currentframe, getframeinfo
import os
import time

from tpsup.modtools import strings_to_funcs, load_module
import platform

if platform.system().lower().startswith("lin"):
    import pwd
    import grp


def tpfind(**opt):
    # https://stackoverflow.com/questions/16039280/mutability-of-the-kwargs-argument-in-python
    # **kwargs is shallow copy
    # https://stackoverflow.com/questions/986006/how-do-i-pass-a-variable-by-reference

    for k in ['paths', 'HandleExps', 'HandleActs', 'FlowExps', 'FlowDirs']:
        if not opt.get(k):
            opt[k] = []

    opt.setdefault('verbose', 0)
    opt.setdefault('maxdepth', 100)

    if len(opt['HandleExps']) != len(opt['HandleActs']):
        raise Exception(f"size mismatch: len(HandleExps)={len(opt['HandleExps'])}, len(HandleActs)={len(opt['HandleActs'])}")

    if len(opt['FlowExps']) != len(opt['FlowDirs']):
        raise Exception(f"size mismatch: len(FlowExps)={len(opt['FlowExps'])}, len(FlowDirs)={len(opt['FlowDirs'])}")

    # https://stackoverflow.com/questions/23749750/reading-a-csv-text-file-with-pkgutil-get-data
    # but this only works with in a package, not from a script
    # source_array = [str(pkgutil.get_data(__package__, 'tpfind_helper.py').decode('utf-8'))]
    #
    # https://stackoverflow.com/questions/3718657/how-to-properly-determine-current-script-directory
    filename = getframeinfo(currentframe()).filename
    path = os.path.dirname(os.path.abspath(filename))

    helper_file = f'{path}/tpfind_helper.py'

    # read the entire file
    with open(helper_file, 'r') as f:
        source_array = [f.read()]

    for name, is_exp in [('HandleExps', 1), ('HandleActs', 0), ('FlowExps', 1)]:
        source_array.append(strings_to_funcs(opt[name], name, is_exp=is_exp, verbose=opt['verbose']))
    source = '\n\n'.join(source_array)

    if opt.get('verbose'):
        print(f'source =\n{source}\n')

    if opt.get('SaveSource'):
        with open(opt['SaveSource'], 'wt') as f:
            f.write(source)
            f.write('\n')

    dummy = load_module(source)

    opt['compiled_HandleExps'] = dummy.HandleExps
    opt['compiled_HandleActs'] = dummy.HandleActs
    opt['compiled_FlowExps'] = dummy.FlowExps

    if opt['verbose'] != 0:
        sys.stderr.write(f'{pformat(opt)}\n')

    for path in opt['paths']:
        if opt['verbose'] != 0:
            sys.stderr.write(f'starting path = {path}\n')
        recursive_path(path, opt['maxdepth'], **opt)


# https://docs.python.org/2/library/stat.html
def recursive_path(_path, _maxdepth, **opt):
    ret_struct = {}

    if not os.path.exists(_path):
        sys.stderr.write('{_path} not exist\n'.format(_path=_path))
        return ret_struct

    if opt.get('Trace'):
        print(_path)

    _type = 'unknown'
    if os.path.islink(_path):
        _type = 'link'
    elif os.path.isdir(_path):
        _type = 'dir'
    elif os.path.isfile(_path):
        _type = 'file'

    r = {'path': _path, 'type': _type}

    _stat = os.lstat(_path)

    frameinfo = None

    # https://docs.python.org/2/library/stat.html
    r['mode'] = _stat.st_mode
    r['dev'] = _stat.st_dev
    r['ino'] = _stat.st_ino
    r['nlink'] = _stat.st_nlink
    r['uid'] = _stat.st_uid
    r['gid'] = _stat.st_gid
    r['size'] = _stat.st_size
    r['atime'] = _stat.st_atime
    r['mtime'] = _stat.st_mtime
    r['ctime'] = _stat.st_ctime

    if platform.system().lower().startswith("lin"):
        # https://stackoverflow.com/questions/7770034/in-python-and-linux
        # -how-to-get-given-users-id
        # https://docs.python.org/2/1ibrary/pwd.html
        _pwd = pwd.getpwuid(r['uid'])
        r['owner'] = _pwd.pw_name

        # https://docs.python.org/2/library/grp.html#module-grp
        _grp = grp.getgrgid(r['gid'])
        r['group'] = _grp.gr_name

    r['atime_local'] = time.strftime('%Y%m%d-%H:%M:%S', time.localtime(r['atime']))
    r['ctime_local'] = time.strftime('%Y%m%d-%H:%M:%S', time.localtime(r['ctime']))
    r['mtime_local'] = time.strftime('%Y%m%d-%H:%M:%S', time.localtime(r['mtime']))

    if opt['verbose'] != 0:
        sys.stderr.write(pformat(r))
        frameinfo = getframeinfo(currentframe())
        sys.stderr.write(f'{frameinfo.filename} {frameinfo.lineno}')

    for exp, act, c_exp, c_act \
            in zip(opt['HandleExps'], opt['HandleActs'], opt['compiled_HandleExps'], opt['compiled_HandleActs']):
        if c_exp(r):
            c_act(r)

    for exp, directive, c_exp in zip(opt['FlowExps'], opt['FlowDirs'], opt['compiled_FlowExps']):
        if c_exp(r):
            if directive == 'exit0':
                sys.exit(0)
            elif directive == 'exit1':
                sys.exit(1)
            elif directive == 'prune' or directive == 'skip':
                return ret_struct
            else:
                sys.stderr.write(f"unknown FlowDir={directive}\n")

    if _maxdepth == 0:
        return ret_struct

    if _type == 'dir':
        for new_path in sorted(os.listdir(_path)):
            recursive_path('{_path}/{new_path}'.format(_path=_path, new_path=new_path), _maxdepth - 1, **opt)


def main():
    usage = textwrap.dedent(""""\
        a better 'find' command
        """)

    examples = textwrap.dedent(""" 
    examples:
        # print the dir tree
        tpfind.py -maxdepth 2 -trace ~/github/tpsup
    
        # use handlers
        tpfind.py -maxdepth 1 -he 're.search("tpstamp", r["path"])' \\
        -ha 'ls(r)' ~/github/tpsup
        
        tpfind.py -he 're.search("tpstamp", r["path"])' \\
        -ha 'os.system("ls -1 " + r["path"])' -he 're.search("tpfind", r["path"])' \\
        -ha 'os.system("ls -1 " + r["path"])' ~/github/tpsup
    
        # flow control, use -trace to confirm
        tpfind.py -trace -fe 're.search("autopath|scripts|proj|lib|i86pc|Linux|[.]git", r["path"])'\\
        -fd 'prune' ~/github/tpsup
    
        tpfind.py -trace -fe 're.search("autopath", r["path"])' -fd 'exit1' ~/github/tpsup; echo $?
    
        # use handlers as a filter
        tpfind.py -he 're.search("scripts", r["path"])' -ha 'ls(r)' ~/github/tpsup
    
        # owner
        tpfind.py -he 'r["owner"] != "tian"' -ha 'ls(r)' ~/github/tpsup
    
        # mtime/now. eg, file changed yesterday, one day is 86400 seconds
        tpfind.py -he 'r["mtime"]<now-86400 and r["mtime"]>now-2*86400' -ha 'ls(r)' ~/github/tpsup
    
        # mode, find file group/other-writable
        # note: in Python 3, octal number must start "0o" or "0O" instead of "0"
        tpfind.py -he 'r["type"] != "link" and r["mode"] & 0o0022' -ha 'ls(r)' ~/github/tpsup
    
        # mode, find dir not executable or readable
        tpfind.py -he 'r["type"] == "dir" and (r["mode"] & 0o0555) != 0o0555' -ha 'ls(r)' ~/github/tpsup
    
        # size, eg, file is bigger than 100K
        tpfind.py -he 'r["size"] >100000' -ha 'ls(r)' ~/github/tpsup
    
        # ifh is the open file handler, the following command find all bash scripts
        # and save the runtime dummy module into ~/dummy.py
        # note: to use b'' in re.search pattern because Python3 force use to open ifh with 'rb'
        # and hence, the pattern has to be b'' (byte literal)
        tpfind.py -saveSource ~/dummy.py -he 'r["type"] == "file"' \\
        -ha 'if re.search(br"^#!.*/bash\\b",ifh.readline()): ls(r)' ~/github/tpsup
        """)

    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description=usage,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples)

    parser.add_argument(
        'paths', default=None, nargs=argparse.REMAINDER,
        help='input path')

    parser.add_argument(
        '-he', '--HandleExps', action='append',
        help="Handle match expression, paired with -ha/--HandleActs")

    parser.add_argument(
        '-ha', '--HandleActs', action='append',
        help="Handle action after matching, paired with -he/--HandleExps")

    parser.add_argument(
        '-fe', '--FlowExps', action='append',
        help="Flow control match expression, paired with -fd/--FlowDirs")

    parser.add_argument(
        '-fd', '--FlowDirs', action='append',
        help="Flow control direction after matching, paired with -fd/--FlowExps")

    parser.add_argument(
        '-maxdepth', dest="maxdepth", default=100, action='store', type=int,
        help="max depth, default 100. the path specified by command line has depth 0")

    parser.add_argument(
        '-saveSource', '--SaveSource', dest="SaveSource", default=None, action='store', type=str,
        help="save the expression source code into this file")

    parser.add_argument(
        '-trace', '--Trace', action='store_true',
        help="print the paths that the script has browsed")

    parser.add_argument(
        '-v', '--verbose', default=0, action="count",
        help='verbose level: -v, -vv, -vvv')

    args = vars(parser.parse_args())

    if args['verbose']:
        sys.stderr.write(f"args =\n{pformat(args)}\n")

    if len(args['paths']) == 0 :
        parser.print_help(file=sys.stderr)
        sys.exit(1)

    # https://pythontips.com/2013/08/04/args-and-kwargs-in-python-explained/
    # *args and **kwargs allow you to pass a variable number of arguments to a function.
    # What does variable mean here is that you do not know before hand that how many
    # arguments can be passed to your function by the user so in this case you use these
    # two keywords.
    # *args is used to send a non-keyworded variable length argument list to the function.
    # **kwargs allows you to pass keyworded variable length of arguments to a function.
    # You should use **kwargs if you want to handle named arguments in a function.
    tpfind(**args)


if __name__ == '__main__':
    main()
