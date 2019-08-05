# import inspect
# from dill.source import getsource
import gzip
import os
import platform
import re
import sys
import time
from contextlib import contextmanager
from inspect import currentframe, getframeinfo
from pprint import pformat

if platform.system().lower().startswith("lin"):
    import pwd
    import grp
# elif platform.system().lower().startswith("win"):
#     import windows specific

# https://stackoverflow.com/questions/34794634/how-to-use-a-variable
# -as-function-name-in-python
# https://stackoverflow.com/questions/131842 81/python-dynamic-
# function-creation-with-custom-names

now = None


def strings_to_func(strings, namespace, *, is_exp=0, logic='all'):
    ret = None

    uncompiled_array = ["def temp(r):"]

    if is_exp == 1:
        if logic == 'any':
            for e in strings:
                uncompiled_array.append("    if {e}:".format(e=e))
                uncompiled_array.append("        return True")
            uncompiled_array.append("    return False")
        elif logic == 'all':
            for e in strings:
                uncompiled_array.append("    if not ({e}):".format(e=e))
                uncompiled_array.append("        return False")
            uncompiled_array.append("    return True")
        else:
            # https://stackoverflow.com/questions/6722210/or-die-in-python
            raise Exception("unknown logic={logic}, expect all/any".format(logic=logic))
    elif is_exp == 0:
        # default is not an expression, can be a assignment , eg, x = 1
        for e in strings:
            uncompiled_array.append("    {e}".format(e=e))
    else:
        raise Exception("unknown is_exp={is_exp}, expect 0/1".format(is_exp=is_exp))

    uncompiled_array.append("ret = temp")

    uncompiled_string = '\n'.join(uncompiled_array)

    exec(uncompiled_string, globals(), namespace)

    return ret


# https://stackoverflow.com/questions/713794/catching-an-exception-while-using-a-python-with-statement
@contextmanager
def get_ifh(filename):
    try:
        if re.search(r'[.]gz$', filename):
            ifh = gzip.open(filename, 'rb')
        else:
            ifh = open(filename, 'rb')
    except IOError as err:
        yield None, err
    else:
        try:
            yield ifh, None
        finally:
            ifh.close()


def string_to_func(string, namespace, *, is_exp=0, **opt):
    # namespace is dictionary. Note: change in dictionary will be passed back to caller
    # http://lucumr.pocoo.org/2011/7/9/python-and-pola/#pass-by-what-exactly
    # 75
    #
    # Python's parameter passing acts a bit different than the languages you're probably used to. Instead of having
    # explicit pass by value and pass by reference semantics, python has pass by name. You are essentially always
    # passing the object itself, and the object's mutability determines whether or not it can be modified. Lists and
    # Dicts are mutable objects. Numbers, Strings, and Tuples are not.

    ret = None

    uncompiled_array = ["def temp(r):"]

    # https://stackoverflow.com/questions/3995034/does-python-re-module-support-word-boundaries-b
    # https://stackoverflow.com/questions/12871066/what-exactly-is-a-raw-string-regex-and-how-can-you-use-it
    indent = ''
    if re.search(r'\bifh\b', string):
        #        # https://docs.python.org/2/library/gzip.html
        #         ifh_opened = True
        #         uncompiled_array.append(""" 
        #     with get_ifh(r['path']) as ifh:
        # """)
        uncompiled_array.append("with get_ifh(r['path']) as ifh:")
        indent = '    '

    # Python makes a big deal between statement (x+=1, print "hell")
    # and expression (x==1, x).
    # "return" can only go before expression
    # https://stackoverflow.com/questions/32383788/python-return-s
    # syntax-error
    if is_exp == 1:
        uncompiled_array.append(f"{indent}    return ({string})")
    elif is_exp == 0:
        # default to non-expression, eg, assignment, like, x=1
        uncompiled_array.append(f"{indent}    {string}")
    else:
        raise Exception("unknown is_exp={is_exp}, expect 0/1".format(is_exp=is_exp))

    uncompiled_array.append("ret = temp")

    uncompiled_string = '\n'.join(uncompiled_array)

    if 'verbose' in opt and opt['verbose'] != 0:
        sys.stderr.write(f'uncompiled_string =\n{uncompiled_string}\n')

    exec(uncompiled_string, globals(), namespace)

    # if 'verbose' in opt and opt['verbose'] != 0:
    #     sys.stderr.write(f'compiled =\n{ret}\n')
    #
    # return ret

def strings_to_funcs(strings, namespace, *, is_exp=0, **opt):
    string_to_func(s, _namespace, is_exp=1, verbose=opt['verbose']) for s in strings


def tpfind(**opt):
    # https://stackoverflow.com/questions/16039280/mutability-of-the-kwargs-argument-in-python
    # **kwargs is shallow copy
    # https://stackoverflow.com/questions/986006/how-do-i-pass-a-variable-by-reference

    _namespace = {}

    for k in ['paths', 'HandleExps', 'HandleActs', 'FlowExps', 'FlowDirs']:
        if k not in opt or opt[k] is None:
            opt[k] = []

    if 'verbose' not in opt:
        opt['verbose'] = 0

    if 'maxdepth' not in opt:
        opt['maxdepth'] = 100

    if len(opt['HandleExps']) != len(opt['HandleActs']):
        raise Exception("size mismatch: len(HandleExps)={l1}, len(HandleActs)={l2}".format(l1=len(opt['HandleExps']),
                                                                                           l2=len(opt['HandleActs'])))

    if len(opt['FlowExps']) != len(opt['FlowDirs']):
        raise Exception("size mismatch: len(FlowExps)={l1}, len(FlowDirs)={l2}".format(l1=len(opt['FlowExps']),
                                                                                       l2=len(opt['FlowDirs'])))

    opt['compiled_HandleExps'] = [string_to_func(s, _namespace, is_exp=1, verbose=opt['verbose']) for s in opt['HandleExps']]
    opt['compiled_HandleActs'] = [string_to_func(s, _namespace, is_exp=0, verbose=opt['verbose']) for s in opt['HandleActs']]
    opt['compiled_FlowExps'] = [string_to_func(s, _namespace, is_exp=1, verbose=opt['verbose']) for s in opt['FlowExps']]

    if opt['verbose'] != 0:
        sys.stderr.write(f'{pformat(opt)}\n')

        global now
        now = time.time()
        sys.stderr.write(f'now = repr(now)\n')

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

    if 'Trace' in opt and opt['Trace']:
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

    if opt['verbose'] != 0:
        getframeinfo(currentframe())
        sys.stderr.write(f'{frameinfo.filename} {frameinfo.lineno}\n')

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


def ls(r):
    # https://realpython.com/python-string-formatting/
    print(
        f'{permissions_to_unix_name(r)} {r["nlink"]:>2} {r["owner"]:>8} {r["group"]:>8} {r["size"]:>9} {r["mtime_local"]} {r["path"]}')


# https://stackoverflow.com/questions/17809386/how-to-convert-a-
# stat-output-to-a-unix-permissions-string
# python 3.3 and above has stat.filemode() to do this
def permissions_to_unix_name(r):
    is_dir = 'd' if r['type'] == 'dir' else '-'
    dic = {'7': 'rwx', '6': 'rw-', '5': 'r-x', '4': 'r--',
           '3': '-wx', '2': '-w-', '1': '--x', '0': '---'}
    perm = str(oct(r['mode'])[-3:])
    return is_dir + ''.join(dic.get(x, x) for x in perm)


def tpeng_lock(plain, salt):
    _MAGIC = 'AccioConfundoLumosNox'
    length = len(plain)
    if not salt:
        salt = _MAGIC

    # https://www.pythoncentral.io/use-python-multiply-strings/
    multplied_salt = length * salt

    # https://guide.freecodecamp.org/python/is-there-a-way-to-substri
    # ng-a-string-in-python/
    magic = multplied_salt[0:length]

    # encrypted = []
    # for i in range(0,length):
    #    encrypted[i] = magic[i] A plain[i]

    # https://stackoverflow.com/questions/2612720/how-to-do-bitwis
    # e-exclusive-or-of-two-strings-in-python
    encrypted = ''.join(chr(ord(a) ^ ord(b)) for a, b in zip(magic, plain))

    escaped = uri_escape(encrypted)

    return escaped


def tpeng_unlock(string, salt):
    _MAGIC = 'AccioConfundoLumosNox'
    unescaped = uri_unescape(string)
    if not salt:
        salt = _MAGIC

    length = len(unescaped)

    # https://www.pythoncentral.io/use-python-multiply-strings/
    multplied_salt = length * salt

    # https://guide.freecodecamp.org/python/is-there-a-way-to-substr
    # ing-a-string-in-python/
    magic = multplied_salt[0:length]

    plain = ''.join(chr(ord(a) ^ ord(b)) for a, b in zip(magic, unescaped))

    return plain


def uri_escape(string):
    escape = {}

    for i in range(0, 256):
        escape[chr(i)] = "%%%02X" % i

        # RFC3986 = '[AA-Za-z0-9\-\._~]';
        # compiled = re.compile(RFC3986)
        # result = re.sub(r"[^A-Za-z0-9\\-\\._~]", escape[r"\1"], string)

    escaped = []

    for c in list(string):
        ord_c = ord(c)
        if ((ord('A') <= ord_c <= ord('Z'))
                or (ord('a') <= ord_c <= ord('z'))
                or (ord('0') <= ord_c <= ord('9'))
                or ord_c == ord('-') or ord_c == ord('.')
                or ord_c == ord('_') or ord_c == ord('~')):
            escaped.append(c)
        else:
            escaped.append(escape[c])

    result = ''.join(escaped)

    return result


def uri_unescape(string):
    # the following is the same as
    # return urllib.unquote(string).decode('utf8')

    _hexdig = '0123456789ABCDEFabcdef'
    _hextochr = dict((a + b, chr(int(a + b, 16)))
                     for a in _hexdig for b in _hexdig)

    res = string.split('%')
    for i in range(1, len(res)):
        item = res[i]
        try:
            res[i] = _hextochr[item[:2]] + item[2:]
        except KeyError:
            res[i] = '%' + item
        except UnicodeDecodeError:
            res[i] = chr(int(item[:2], 16)) + item[2:]
    return "".join(res)
