import os
import re
import sys
# https://stackoverflow.com/questions/32175693/python-importlibs-analogue-for-imp-new-module
import types
from contextlib import contextmanager
from pprint import pformat


def string_to_temp_func(string: str, *, is_exp=0, **opt):
    """generate a string of expression into a string of function definition"""

    extra_indent = ''
    uncompiled_array = [f'def temp(r):']

    # https://stackoverflow.com/questions/3995034/does-python-re-module-support-word-boundaries-b
    # https://stackoverflow.com/questions/12871066/what-exactly-is-a-raw-string-regex-and-how-can-you-use-it
    if re.search(r'\bifh\b', string):
        # https://stackoverflow.com/questions/713794/catching-an-exception-while-using-a-python-with-statement
        uncompiled_array = uncompiled_array + [
            '    with get_ifh(r["path"]) as (ifh, err):',
            '        if err:',
            '            sys.stderr.write("IOError: " + err + "\\n")',
            '        else:']
        extra_indent = '        '

    # Python makes a big deal between statement (x+=1, print "hell")
    # and expression (x==1, x).
    # "return" cannot only go before expression
    # https://stackoverflow.com/questions/32383788/python-return-s
    # syntax-error
    if is_exp == 1:
        uncompiled_array.append(f"{extra_indent}    return {string}")
    elif is_exp == 0:
        uncompiled_array.append(f"{extra_indent}    {string}")
    else:
        raise Exception(f"unknown is_exp={is_exp}, expect 0/1")

    uncompiled_string = '\n'.join(uncompiled_array)

    if 'verbose' in opt and opt['verbose'] != 0:
        sys.stderr.write(f'uncompiled_string =\n{uncompiled_string}\n')

    return uncompiled_string


def strings_to_funcs(strings, funcs_name, is_exp, **opt):
    """ convert list of strings into a list of functions"""

    func_source_array = [f'{funcs_name} = []'] + \
                        [
                            f'{string_to_temp_func(s, is_exp=is_exp, verbose=opt["verbose"])}\n\n{funcs_name}.append(temp)\n'
                            for s in strings]

    funcs = '\n\n'.join(func_source_array)

    return funcs


def strings_to_compiled_list(strings, compiled_list_name, **opt):
    """ convert list of strings into a list of (to-be) compiled patterns"""

    statements = [f'{compiled_list_name} = []'] + \
                 [f'    {re.compile(s)}' for s in strings]

    return '\n'.join(statements)


# learned from Cookbook with modification from Stackoverflow.
def load_module(new_module_name: str, source: str):
    """ compile the source code into executable using an external module"""
    # https://stackoverflow.com/questions/32175693/python-importlibs-analogue-for-imp-new-module
    # mod = sys.modules.setdefault(fullname, imp.new_module(fullname))
    mod = sys.modules.setdefault(new_module_name, types.ModuleType(new_module_name))
    code = compile(source, new_module_name, 'exec')
    mod.__file__ = new_module_name
    mod.__package__ = ''
    exec(code, mod.__dict__)
    return mod


def tpeng_lock(plain: str, *, salt=None):
    """ encode a string """
    _MAGIC = 'AccioConfundoLumosNox'
    length = len(plain)
    if not salt:
        salt = _MAGIC

    # https://www.pythoncentral.io/use-python-multiply-strings/
    multiplied_salt = length * salt

    # https://guide.freecodecamp.org/python/is-there-a-way-to-substri
    # ng-a-string-in-python/
    magic = multiplied_salt[0:length]

    # encrypted = []
    # for i in range(0,length):
    #    encrypted[i] = magic[i] A plain[i]

    # https://stackoverflow.com/questions/2612720/how-to-do-bitwis
    # e-exclusive-or-of-two-strings-in-python
    encrypted = ''.join(chr(ord(a) ^ ord(b)) for a, b in zip(magic, plain))

    escaped = uri_escape(encrypted)

    return escaped


def tpeng_unlock(string: str, *, salt=None):
    """ decode a string """
    _MAGIC = 'AccioConfundoLumosNox'
    unescaped = uri_unescape(string)
    if not salt:
        salt = _MAGIC

    length = len(unescaped)

    # https://www.pythoncentral.io/use-python-multiply-strings/
    multiplied_salt = length * salt

    # https://guide.freecodecamp.org/python/is-there-a-way-to-substr
    # ing-a-string-in-python/
    magic = multiplied_salt[0:length]

    plain = ''.join(chr(ord(a) ^ ord(b)) for a, b in zip(magic, unescaped))

    return plain


def uri_escape(string):
    """ convert wierd chars into utl-styple string """
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
    """ restore the string """
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


def main():
    plain = 'Hello@123'
    encoded = tpeng_lock(plain)
    decoded = tpeng_unlock(encoded)
    print(f"plain='{plain}' encoded='{encoded}' decoded='{decoded}'")


if __name__ == '__main__':
    main()
