import os
import re
import subprocess
import sys
from pprint import pformat
from typing import List, Dict
import tpsup.csvtools
import tpsup.envtools


def tpsup_lock(plain: str, *, salt=None):
    """ encode a string
    >>> tpsup_lock("hello world")
    '%29%06%0F%05%00c%18%01%14%19%0A'
    >>> tpsup_unlock("%29%06%0F%05%00c%18%01%14%19%0A")
    'hello world'
    """
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


def tpsup_unlock(string: str, *, salt=None):
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


class EntryBook:
    command_pattern = re.compile("tpentry{(.+?)}{(.+?)}")  # class attribute

    def __init__(self, **opt):
        self.verbose = opt.get('verbose', 0)
        self.env = tpsup.envtools.Env()
        file = opt.get('book', None)
        if file is None:
            file = self.env.home_dir + "/.tpsup/book.csv"

        if not os.path.exists(file):
            raise RuntimeError(f'{file} not found')

        #if self.env.isLinux or self.env.isCygwin or self.env.isGitBash:
        if self.env.isLinux:
            st = os.stat(file)
            file_perm = st.st_mode & 0o777
            if file_perm != 0o600:
                raise RuntimeError(f'{file} permission is {file_perm:o}; required 600')

        self.file = file
        self.entry_by_key = {}

    def get_entry_by_key(self, key: str) -> Dict:
        if key in self.entry_by_key:
            return self.entry_by_key[key]

        opt2 = {'MatchExps': [f'r["key"] == "{key}"']}
        dictlist = list(tpsup.csvtools.QueryCsv(self.file, **opt2))
        if len(dictlist) == 0:
            raise RuntimeError(f"{self.file} does not contain key={key}: {dictlist}")
        elif len(dictlist) > 1:
            raise RuntimeError(f'{self.file} has multiple key={key} defined: {dictlist}')

        entry = dictlist[0]

        entry['decoded'] = tpsup_unlock(entry['encoded'])

        self.entry_by_key[key] = entry
        return self.entry_by_key[key]

    def entry_substitute(self, part: str, executable: str, **opt) -> str:
        verbose = opt.get('verbose', 0)

        while True:
            m = EntryBook.command_pattern.search(part)  # class attribute
            # re.match() vs re.search(): match() is from beginning, search() is anywhere
            if m:
                key = m.group(1)
                attr = m.group(2)

                entry = self.get_entry_by_key(key)
                if not (attr in entry):
                    raise RuntimeError(f"{attr} is not field in {self.file}")

                commandpattern = entry.get('commandpattern', None)
                if commandpattern is None:
                    raise RuntimeError(f"commandpattern is not defined for key {key} in {self.file}")
                if not re.search(commandpattern, executable):
                    raise RuntimeError(f"executable={executable} does not match commandpattern={commandpattern}")

                if verbose:
                    # {{ }} are escapes for { } in f-string
                    print(f"replaced tpentry{{{key}}}{{{attr}}}", file=sys.stderr)
                part = part.replace(f"tpentry{{{key}}}{{{attr}}}", entry[attr])
            else:
                return part

    def run_cmd(self, encoded_cmd, **opt):
        verbose = opt.get('verbose', 0)

        command_list = []
        input_type = type(encoded_cmd)
        if input_type is list:
            command_list = encoded_cmd
        elif input_type is str:
            command_list = tokenize_command_string(encoded_cmd)

        # tpentry.py -v -- /usr/bin/mysql -u tian -ptpentry{tiandb}{decoded} tiandb
        # args =
        # {'book': None,
        #  'cmdAndArgs': ['--',
        #                 '/usr/bin/mysql',
        #                 '-u',
        #                 'tian',
        #                 '-ptpentry{tiandb}{decoded}',
        #                 'tiandb'],
        #  'verbose': True}
        while command_list[0] == '--':
            command_list = command_list[1:]

        executable = command_list[0]
        for i in range(0, len(command_list)):
            command_list[i] = self.entry_substitute(command_list[i], executable, verbose=verbose)

        # DISABLE VERBOSE to avoid show password
        # if verbose:
        #    sys.stderr.write(f"command_list =\n{pformat(command_list)}\n")

        # os.system run with a string, not a List
        #return os.system(command_list)

        return subprocess.run(command_list)


def tokenize_command_string(string: str) -> List:
    tokens = []
    chars = []
    token_started = False
    open_double = False
    open_single = False
    for c in string:
        if open_double:
            if c == '"':
                open_double = False
            else:
                chars.append(c)
            continue

        if open_single:
            if c == '"':
                open_single = False
            else:
                chars.append(c)
            continue

        if c == '"':
            open_double = True
            token_started = True
        elif c == "'":
            open_single = True
            token_started = True
        elif c.isspace():
            if token_started:
                tokens.append(''.join(chars))
                token_started = False
                chars = []
        else:
            chars.append(c)
            token_started = True
    if open_single:
        raise RuntimeError("unmatched single quote at the end")
    elif open_double:
        raise RuntimeError("unmatched single quote at the end")
    elif token_started:
        tokens.append(''.join(chars))
    return tokens


def main():
    plain = 'Hello@123'
    encoded = tpsup_lock(plain)
    decoded = tpsup_unlock(encoded)
    print(f"plain='{plain}' encoded='{encoded}' decoded='{decoded}'")

    string = '"C:\Program Files\Python37\python.exe" -h'
    print(f"string={string}")
    print(f"tokens =\n{pformat(tokenize_command_string(string))}")

    env = tpsup.envtools.Env()

    if env.isWindows:
        string = '"C:\Program Files\Python37\python.exe" --version'
        print(f"string={string}")
        EntryBook().run_cmd(string, verbose=1)

    print(f"\ndoctest started. we should see no output if successful.")
    import doctest
    doctest.testmod()
    print(f"\ndoctest ended. we should see no output if successful.")

if __name__ == '__main__':
    main()
