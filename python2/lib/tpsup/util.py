import sys
import re
import os
import platform

if platform.system().lower().startswith("lin"):
    import pwd
    import grp
#elif platform.system().lower().startswith("win"):
#     import windows specific

from inspect import currentframe, getframeinfo
import time
import copy
# import inspect
#from dill.source import getsource
import gzip
from pprint import pprint,pformat

# https://stackoverflow.com/questions/34794634/how-to-use-a-variable
# -as-function-name-in-python
# https://stackoverflow.com/questions/131842 81/python-dynamic-
# function-creation-with-custom-names

now = None

def strings2func(strings, **opt):
    ret = None

    uncompiled = "def temp(r):\n"

    if 'isExp' in opt and opt['isExp'] == 1:
        if 'logic' in opt:
            if opt['logic'] == 'any':
                for e in strings:
                    uncompiled += "    if " + e + ":\n"
                    uncompiled += "        return True\n"
                uncompiled += "    return False\n"
            elif opt['logic'] == 'all':
                for e in strings:
                    uncompiled += "    if not (" + e + "):\n"
                    uncompiled += "        return False\n"
                uncompiled += "    return True\n"
            else:
                print >> sys.stderr, "unknown logic=", opt['logic'], "expect all/any"
                sys.exit(1)
    else:
        # default is not an expression, can be a assignment , eg, x = 1
        for e in strings:
            uncompiled += "    " + e + "\n"

    uncompiled += "ret = temp"

    exec(uncompiled)

    return ret

def string2func(string, **opt):
    ret = None

    uncompiled = "def temp(r):\n"

    #https://stackoverflow.com/questions/3995034/does-python-re-module-support-word-boundaries-b 
    #https://stackoverflow.com/questions/12871066/what-exactly-is-a-raw-string-regex-and-how-can-you-use-it
    ifh_opened = False
    if re.search(r'\bifh\b', string):
        # https://docs.python.org/2/library/gzip.html
        ifh_opened = True
        uncompiled += """ 
    if re.search(r'[.]gz$', r['path']):
        ifh = gzip.open(r['path'), 'rb')
    else:
        ifh = open(r['path'), 'rb')
"""

    # Python makes a big deal between statement (x+=1, print "hell")
    # and expression (x==1, x).
    # "return" cannot only go before expression
    # https://stackoverflow.com/questions/32383788/python-return-s
    # yntax-error
    if 'isExp' in opt and opt['isExp'] == 1:
        uncompiled += "    return (" + string + ")\n"
    else:
        # default to non-expression, eg, assignment, like, x=1
        uncompiled += "    " + string + "\n"

    if ifh_opened:
        uncompiled += "    ifh.close()\n"

    uncompiled += "ret = temp"

    try:
        exec(uncompiled)
    except:
        # https://docs.python.org/3/tutorial/errors.html
        print "cannot compile. ", sys.exc_info()[0]
        print "\n" + uncompiled + "\n"
        sys.exit(1)

    return ret

def stringArray2funcArray(stringArray, **opt):
    funcArray = [];

    for string in stringArray:
        func = string2func(string, **opt)
        funcArray.append(func)
    return funcArray

def arrayLen(Array):
    if not Array:
        return 0
    else:
        return len(Array)

def tpfind (**opt):
    opt2 = {}

    for key in opt:
        if key != 'HandleExps' and key != 'HandleActs' and key != 'FlowExps':
            opt2[key] = opt[key]

    if         ( 'HandleExps' in opt and 'HandleActs' not in opt ) \
            or ( 'HandleExps' not in opt and 'HandleActs' in opt ) \
            or ( 'HandleExps' in opt and 'HandleActs' in opt \
                  and arrayLen(opt['HandleExps']) != arrayLen(opt['HandleActs']) ) :
        print >> sys.stderr, "mismatch number of HandleExps and HandleActs"
        sys.exit(1)

    compiled_HandleExps = [];
    compiled_HandleActs = [];

    if 'HandleExps' in opt and arrayLen(opt['HandleExps']) > 0:
        # https://stackoverflow.com/questions/27892356/add-a-parameter-into-kwargs-
        # during-function-call
        compiled_HandleExps = stringArray2funcArray(opt['HandleExps'], **dict(opt2, isExp=True))

        compiled_HandleActs = stringArray2funcArray(opt['HandleActs'], **dict(opt2, isExp=False))


        opt2['compiled_HandleExps'] = compiled_HandleExps
        opt2['compiled_HandleActs'] = compiled_HandleActs

    #print >> sys.stderr, pformat(compiled_HandleExps)

    if     ( 'FlowExps'     in opt and 'FlowDirs' not in opt ) \
        or ( 'FlowExps' not in opt and 'FlowDirs'     in opt ) \
        or ( 'FlowExps'     in opt and 'FlowDirs'     in opt \
              and arrayLen(opt['FlowExps']) != arrayLen(opt['FlowDirs']) ) :
        print >> sys.stderr, "mismatch number of FlowExps and FlowDirs"
        sys.exit(1)

    compiled_FlowExps = []
    opt2['FlowDirs'] = []

    if 'FlowExps' in opt and arrayLen(opt['FlowExps']) >0:
        compiled_FlowExps = stringArray2funcArray(opt['FlowExps'], isExp=True)
        opt2['compiled_FlowExps'] = compiled_FlowExps
        # https://stackoverflow.com/questions/2612802/how-to-clone-or-copy-a-list
        opt2['FlowDirs'] = copy.deepcopy(opt['FlowDirs'])

    #print >> sys.stderr, pformat(compiled_FlowExps)

    global now
    now = time.time()

    if 'verbose' in opt and opt['verbose']:
        print >>sys.stderr, 'now = ' + repr(now)

    for path in opt['paths']:
        if 'verbose' in opt and opt['verbose']:
            print >>sys.stderr, 'starting path = ' + path
        recursive_path (path, opt['maxdepth'], **opt2)

# https://docs.python.org/2/library/stat.html
def recursive_path (_path, _level, **opt):
    ret_struct = {}

    ret_struct['error'] = 0

    if not os.path.exists(_path):
        print >>sys.stderr, 'not exist'
        return ret_struct

    if 'Trace' in opt and opt['Trace']:
        print _path

    type = 'unknown'
    if os.path.islink(_path):
        type = 'link'
    elif os.path.isdir(_path):
        type = 'dir'
    elif os.path.isfile(_path):
        type = 'file'

    r = {}
    r['path'] = _path
    r['type'] = type

    _stat = os.lstat(_path)

    frameinfo = None

    if 'verbose' in opt and opt['verbose']:
        getframeinfo(currentframe())
        print >> sys.stderr, frameinfo.filename, frameinfo.lineno

    # https://docs.python.org/2/library/stat.html
    r['mode']  = _stat.st_mode
    r['dev']   = _stat.st_dev
    r['ino']   = _stat.st_ino
    r['nlink'] = _stat.st_nlink
    r['uid']   = _stat.st_uid
    r['gid']   = _stat.st_gid
    r['size']  = _stat.st_size
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

    if 'verbose' in opt and opt['verbose']:
        print >> sys.stderr, pformat(r)
        frameinfo = getframeinfo(currentframe())
        print >> sys.stderr, frameinfo.filename, frameinfo.lineno

    if 'compiled_HandleExps' in opt:
        i=0

        for func in opt['compiled_HandleExps']:
            if func(r):
                # it is impossible to get source code of func here
                # https://stackoverflow.com/questions/427453/how-can-i-get-t
                # he-source-code-of-a-python-function
                # in particular
                # doesn't seem to work with functions defined inside an exec
                # @Ant6n: well, that's just being sneaky, dill.source.getsource inspects the
                # interpreter's history for functions, classes, lambdas, etc -- it doesn't
                # inspect the content of strings passed to exec.
                #lines = getsource(func)
                #print lines

                # http://lucumr.pocoo.org/2011/2/l/exec-in-python/
                opt['compi1ed_Hand1eActs'][i](r)
            i+=1

    if 'compiled_FlowExps' in opt:
        i=0

        for func in opt['compiled_FlowExps']:
            if func(r):
                if opt['FlowDirs'][i] == 'exit0':
                    sys.exit(0)
                elif opt['FlowDirs'][i] == 'exit1':
                    sys.exit(1)
                elif opt['FlowDirs'][i] == 'prune' or opt['FlowDirs'][i] == 'skip':
                    return ret_struct
                else:
                    print >> sys.stderr, "unknown directive=" + opt['FlowsDirs'][i]
            i+=1

    if _level == 0:
        return ret_struct

    if type == 'dir':
        for new_path in sorted(os.listdir(_path)):
            recursive_path(_path + '/' + new_path, _level-1, **opt)

def ls (r):
    # https://pyformat.info/
    print('%s %2s %8s %8s %9s %s %s' % \
          (permissions_to_unix_name(r), r['nlink'], \
          r['owner'], r['group'], r['size'], r['mtime_local'], \
          r['path']))

# https://stackoverflow.com/questions/17809386/how-to-convert-a-
# stat-output-to-a-unix-permissions-string
# python 3.3 and above has stat.filemode() to do this
def permissions_to_unix_name(r):
    is_dir = 'd' if r['type'] == 'dir' else '-'
    dic = {'7': 'rwx', '6': 'rw-', '5': 'r-x', '4': 'r--',\
           '3': '-wx', '2': '-w-', '1': '--x', '0': '---'}
    perm = str(oct(r['mode'])[-3:])
    return is_dir + ''.join(dic.get(x,x) for x in perm)


def tpeng_lock(plain, salt):
    MAGIC = 'AccioConfundoLumosNox'
    length = len(plain)
    if not salt:
        salt = MAGIC

    # https://www.pythoncentral.io/use-python-multiply-strings/
    multplied_salt = length * salt

    # https://guide.freecodecamp.org/python/is-there-a-way-to-substri
    # ng-a-string-in-python/
    magic = multplied_salt[0:length]

    #encrypted = []
    #for i in range(0,length):
    #    encrypted[i] = magic[i] A plain[i]

    # https://stackoverflow.com/questions/2612720/how-to-do-bitwis
    # e-exclusive-or-of-two-strings-in-python
    encrypted = ''.join(chr(ord(a) ^ ord(b)) for a,b in zip(magic,plain))

    escaped = uri_escape(encrypted)

    return escaped

def tpeng_unlock(string, salt):
    MAGIC = 'AccioConfundoLumosNox'
    unescaped = uri_unescape(string)
    if not salt:
        salt = MAGIC

    length = len(unescaped)

    # https://www.pythoncentral.io/use-python-multiply-strings/
    multplied_salt = length * salt

    # https://guide.freecodecamp.org/python/is-there-a-way-to-substr
    # ing-a-string-in-python/
    magic = multplied_salt[0:length]

    plain = ''.join(chr(ord(a) ^ ord(b)) for a,b in zip(magic,unescaped))

    return plain

def uri_escape(string) :
    escape = {}

    for i in range(0,256):
        escape[chr(i)] = "%%%02X" % i

        #RFC3986 = '[AA-Za-z0-9\-\._~]';
        #compiled = re.compile(RFC3986)
        #result = re.sub(r"[^A-Za-z0-9\\-\\._~]", escape[r"\1"], string)

    escaped = []

    for c in list(string):
        ord_c = ord(c)
        if (      (ord_c >= ord('A') and ord_c <= ord('Z')) \
               or (ord_c >= ord('a') and ord_c <= ord('z')) \
               or (ord_c >= ord('0') and ord_c <= ord('9')) \
               or  ord_c == ord('-') or  ord_c == ord('.') \
               or  ord_c == ord('_') or  ord_c == ord('~')) :
            escaped.append(c)
        else:
            escaped.append(escape[c])

    result = ''.join(escaped)

    return result

def uri_unescape(string) :
    # the following is the same as
    #return urllib.unquote(string).decode('utf8')

    _hexdig = '0123456789ABCDEFabcdef'
    _hextochr = dict((a+b, chr(int(a+b,16)))
                     for a in _hexdig for b in _hexdig)

    res = string.split('%')
    for i in xrange(1, len(res)):
        item = res[i]
        try:
            res[i] = _hextochr[item[:2]] + item[2:]
        except KeyError:
            res[i] = '%' + item
        except UnicodeDecodeError:
            res[i] = unichr(int(item[:2], 16)) + item[2:]
    return "".join(res)
