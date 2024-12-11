import functools
import os
import getpass
import platform
from pprint import pformat
import re
import sys
import time
from typing import Literal
import subprocess


def flush_rightaway(func):
    @functools.wraps(func)
    def flushed(*args, **kwargs):
        result = func(*args, **kwargs)
        sys.stderr.flush()
        return result

    return flushed


cached_env = None


class Env:
    def __init__(self, **opt):
        global cached_env

        self.verbose = opt.get("verbose", 0)

        if cached_env is not None:
            if self.verbose:
                print(f"cached_env = {cached_env}")

            # self = cached_env # this does not work, so use below

            for attr in cached_env.__dict__:
                self.__dict__[attr] = cached_env.__dict__[attr]
            return

        self.uname = platform.uname()
        # pprint(self.uname)
        # system='Windows', node='tianpc', release='10', version='10.0.19044', machine='AMD64')
        # uname_result(system='Linux', node='linux1', release='4.15.0-112-generic', version='#113-Ubuntu SMP Thu Jul 9 23:41:39 UTC 2020', machine='x86_64', processor='x86_64')
        self.system = self.uname.system
        self.home_dir = os.path.expanduser("~")
        self.isGitBash = False
        self.isCygwin = False
        self.isLinux = False
        self.isWindows = False
        self.isMac = False
        self.isDarwin = False
        self.environ = os.environ
        # self.user = os.getlogin()
        # the above os.getlogin() stops working:
        #     elf.user = os.getlogin()
        #   OSError: [Errno 6] No such device or address
        # see https://bugs.python.org/issue40821
        self.user = getpass.getuser()
        self.PATH = os.environ.get("PATH", "")
        self.python_version = platform.python_version()
        self.ls_cmd = "ls"
        self.hostname = platform.node()
        # self.hostname = platform.node().split('.')[0]  # short name

        # this will be used by cygwin and gitbash terminals
        self.term = {}

        if re.search("Windows", self.system, re.IGNORECASE):
            self.isWindows = True
            # >>> platform.uname()
            # uname_result(system='Windows', node='tianpc', release='10', version='10.0.19044', machine='AMD64')
            self.os_major, self.os_minor, *_ = self.uname.version.split('.')

            # this will be used by python.exe
            self.ls_cmd = "dir"
            # self.tmpdir = f"C:\\Users\\{os.environ['USERNAME']}\\AppData\\Local\\Temp"
            # self.home_dir = f"C:\\Users\\{os.environ['USERNAME']}"

            # C drive home, sometimes it is different from real home
            self.home_dir = f"C:\\Users\\{self.user}"
            self.tmpdir = f"{self.home_dir}\\AppData\\Local\\Temp"

            # default term setting is batch
            self.term['term'] = "batch"
            self.term['tmpdir'] = self.tmpdir
            self.term['ls_cmd'] = "dir"
            self.term['/'] = "/"

            CMDCMDLINE = os.environ.get("CMDCMDLINE", None)
            # batch signature
            # CMDCMDLINE=C:\Windows\system32\cmd.exe
            # but since we check this env from python, CMDCMDLINE is set.
            # therefore, we put batch term as default on above.
            if CMDCMDLINE:
                print(f"CMDCMDLINE={CMDCMDLINE}")
            elif os.environ.get("MSYSTEM", "") == "MINGW64":
                # GitBash signature
                # MSYSTEM=MINGW64
                self.isGitBash = True
                self.term['term'] = "gitbash"
                self.term['tmpdir'] = "/tmp"
                self.term['ls_cmd'] = "ls"
                try:
                    self.term['/'] = subprocess.run(
                        ["cygpath", "-m", "/"], capture_output=True, text=True
                    ).stdout.strip()  # bash/perl's backtick-equivalent
                except Exception as e:
                    print(e)
                    print('"cygpath -m /" failed.')
            elif "MINTTY_SHORTCUT" in os.environ:
                # Cygwin signature:
                # MINTTY_SHORTCUT=/cygdrive/c/Users/william/AppData/Roaming/Microsoft/Internet
                #  Explorer/Quick Launch/User Pinned/TaskBar/Cygwin64 Terminal.lnk
                # see https://mintty.github.io/mintty.1.html
                #   "sets environment variable MINTTY_SHORTCUT"
                self.isCygwin = True
                self.term['term'] = "cygwin"
                self.term['tmpdir'] = "/tmp"
                self.term['ls_cmd'] = "ls"
                # because cygwin's home dir is C:\cygwin64\home\<username>, likely not the normal windows's home
                # dir C:/users/<username>. use C:/users/<username> instead
                # self.home_dir = f'C:/Users/{os.environ["USERNAME"]}'
        elif re.search("Linux", self.system, re.IGNORECASE):
            self.isLinux = True
            self.tmpdir = "/tmp"
            # >>> platform.uname()
            # uname_result(system='Linux', node='linux1', release='4.15.0-112-generic', version='#113-Ubuntu SMP Thu Jul 9 23:41:39 UTC 2020', machine='x86_64', processor='x86_64')
            self.os_major, self.os_minor, *_ = self.uname.release.split('.')
        elif re.search("^Darwin", self.system, re.IGNORECASE):
            self.isDarwin = True
            self.isMac = True
            self.tmpdir = "/tmp"
            # >>> platform.uname()
            # uname_result(system='Linux', node='linux1', release='4.15.0-112-generic', version='#113-Ubuntu SMP Thu Jul 9 23:41:39 UTC 2020', machine='x86_64', processor='x86_64')
            self.os_major, self.os_minor, *_ = self.uname.release.split('.')
        else:
            raise RuntimeError(f"unsupported OS = {pformat(self.uname)}")

        if self.verbose:
            print(f"saving env to cache")
        cached_env = self

    def __str__(self):
        strings = []
        for attr in sorted(self.__dict__):
            strings.append(f"{attr} = {self.__dict__[attr]}")
        return "\n".join(strings)

    def adapt(self):
        if self.isCygwin or self.isGitBash:
            # https://stackoverflow.com/questions/34668972/cmd-and-git-bash-have-a-different-result-when-run-a-python-code
            # overwrite the standard function
            sys.stderr.write = flush_rightaway(sys.stderr.write)

    def adjpath(self, path: str):
        if self.isWindows and not (self.isCygwin or self.isGitBash):
            return path.replace("/", "\\")
        else:
            return path.replace("\\", "/")

    def ls(self, path: str):
        os.system(f'{self.ls_cmd} "{self.adjpath(path)}"')


def cygpath(path: str, direction: Literal["win2cyg", "cyg2win"], **opt):
    # /cygdrive/c/Program Files;/cygdrive/c/Users;/cygdrive/d
    # c:/Program Files;c:/Users;d:
    if direction == "win2cyg":
        if opt.get("useRe", False):
            # use regex, which is not reliable as it can only
            # handle /cygdrive/..., but cannot convert /home/username
            path2 = re.sub(r"(.):(.*)(;?)", r"/cygdrive/\1/\2\3", path)
            path2.replace("\\", "/")
        else:
            # use cygpath command is more reliable, but slower as it calls
            # external command
            # the following works for python 3.7+
            # strip() is to remove the \n
            path2 = subprocess.run(
                ["cygpath", "-u", path], capture_output=True, text=True
            ).stdout.strip()
    else:
        if opt.get("useRe", False):
            path2 = re.sub(r"/cygdrive/(.)(.*?)(;?)", r"\1:\2\3", path)
        else:
            path2 = subprocess.run(
                ["cygpath", "-m", path], capture_output=True, text=True
            ).stdout.strip()
    return path2


def restore_posix_paths(paths: list, **opt) -> list:
    # by default, gitbash converts / to C:/Program Files/Git
    # for example, xpath=/html becomes xpath=C:/Program Files/Git/html
    # this function converts C:/Program Files/Git/html back to /html
    # so that we can use xpath=/html in our code
    my_env = Env()
    if (not 'term' in my_env.__dict__) or (not my_env.term.get('term', None) == 'gitbash'):
        # linux (ubuntu, WSL) and gitbash don't need to change PATH
        return paths

    new_paths = []
    for old_path in paths:
        if type(old_path) != str:
            print(
                f"tpsup.env: restore_posix_paths: skip non-string '{old_path}'")
            new_paths.append(old_path)
            continue
        new_path = old_path.replace(my_env.term['/'], '/')
        new_paths.append(new_path)
        if old_path != new_path:
            print(f"tpsup.env: restore_posix_paths: {old_path} -> {new_path}")
    return new_paths


def get_tmp_dir(**opt) -> str:
    return Env(**opt).tmpdir


def get_home_dir(**opt) -> str:
    home_dir = Env(**opt).home_dir
    term_type = get_term_type(**opt)
    if term_type != 'batch':
        # change backslash to forward slash
        home_dir = home_dir.replace('\\', '/')
    return home_dir


def get_user(secure: bool = False, **opt):
    # https://stackoverflow.com/questions/842059
    if secure:
        myenv = Env(**opt)
        if myenv.isWindows:
            import win32api  # pip install pywin32
            return win32api.GetUserName()
        elif myenv.isLinux or myenv.isDarwin:
            import pwd
            return pwd.getpwuid(os.getuid()).pw_name
    else:
        # getpass.getuser() is portable but it looks at the values of various
        # environment variables to determine the user name. Therefore,
        # this function should not be relied on for access control purposes
        return getpass.getuser()


def get_user_fullname(user: str = None, **opt) -> str:
    # separate get_user_fullname() and query_user_fullname() so that
    # we can add a cache layer

    verbose = opt.get('verbose', False)

    myself = getpass.getuser()
    if user is None:
        user = getpass.getuser()

    full_name = None
    if user == myself:
        # cache for myself
        env = Env()

        cache_dir = env.home_dir + '/.tpsup'
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            print(f"create cache dir {cache_dir}")
        cache_file = cache_dir + '/my_user_fullname.cache'
        if os.path.exists(cache_file):
            if verbose:
                print(f"read user fullname from cache file {cache_file}")
            with open(cache_file) as fh:
                full_name = fh.read().strip()
            if full_name is not None and full_name != '':
                return full_name
            else:
                if verbose:
                    print(f"cache file is empty, will query again")

        full_name = query_user_fullname(user, **opt)
        if full_name is None or full_name == '':
            return None

        with open(cache_file, 'w') as fh:
            fh.write(full_name)
        return full_name
    else:
        # no cache for other users
        return query_user_fullname(user, **opt)


def query_user_fullname(user: str, **opt) -> str:
    verbose = opt.get('verbose', False)

    full_name = None
    env = Env()
    if env.isWindows:
        # cmd = 'wmic useraccount where name="william" get fullname /value'
        # cmd = 'wmic useraccount where name="%username%" get fullname /value'
        # cmd = cmd.replace('%username%', user)
        user_source = os.environ.get('TPSUP_USER_SOURCE', 'wmic')
        cmd = f"get_user_fullname.cmd {user_source} {user}"

        if verbose:
            print(f"cmd={cmd}")

        ps = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = ps.communicate()[0].decode()
        if verbose:
            print(f"output='{output}'")

        # Extract the full name from the output
        full_name = output.strip()
    elif env.isLinux or env.isMac:
        # only available in linux, not windows. therefore, we need to put it here.
        import pwd
        full_name = pwd.getpwnam(getpass.getuser()).pw_gecos.split(',')[0]
    else:
        raise RuntimeError(f"unsupported OS = {env.uname}")
    return full_name


def get_user_firstlast(user: str = None, **opt) -> str:
    # convert "last, first" to "first last"
    full_name = get_user_fullname(user, **opt)
    if full_name is None:
        return None

    if ', ' in full_name:
        (last, first) = full_name.split(', ')
        return f"{first} {last}"
    else:
        return full_name


re_split = None


def path_contains(dir: str, regex=False,  **opt):
    verbose = opt.get('verbose', False)
    if not regex:
        native_dir = os.path.normpath(dir)

    if not (env_string := opt.get('env_string', None)):
        env_var = opt.get('env_var', "PATH")
        env_string = os.environ.get(env_var)

    if verbose:
        print(f"env_var={env_var}")
        print(f"env_string={env_string}")

    results = []
    splitted_env_string = env_string.split(os.pathsep)
    if verbose:
        print(f"splitted_env_string={pformat(splitted_env_string)}")
    for p in splitted_env_string:
        native_p = os.path.normpath(p)

        if regex:
            if re.search(dir, native_p) or re.search(dir, p):
                results.append(p)
        elif native_p == native_dir:
            results.append(p)
    return results


def add_path(dir: str, **opt) -> str:
    verbose = opt.get('verbose', 0)

    env_var = opt.get('env_var', "PATH")
    env_string = os.environ.get(env_var, '')
    native_dir = os.path.normpath(dir)

    if verbose > 1:
        print(f"old {env_var}={env_string}")

    paths = env_string.split(os.pathsep)
    native_paths = [os.path.normpath(p) for p in paths]
    if opt.get('place', None) == 'prepend':
        # len(list): get length of a list
        if len(native_paths) and native_paths[0] == native_dir:
            # already in the first place
            if verbose:
                print(f"dir={dir} is already in the first place of {env_var}")
            new_env_string = env_string
        else:
            new_paths = [native_dir] + \
                [p for p in native_paths if p != native_dir]
            new_env_string = os.pathsep.join(new_paths)
            os.environ[env_var] = new_env_string
    elif opt.get('place', None) == 'append':
        if len(native_paths) > 0 and native_paths[-1] == native_dir:
            # already in the last place
            if verbose:
                print(f"dir={dir} is already in the last place of {env_var}")
            new_env_string = env_string
        else:
            new_paths = [p for p in native_paths if p !=
                         native_dir] + [native_dir]
            new_env_string = os.pathsep.join(new_paths)
            os.environ[env_var] = new_env_string
    else:
        if path_contains(dir, **opt):
            if verbose:
                print(f"dir={dir} is already in {env_var}")
            new_env_string = env_string
        else:
            new_env_string = env_string + os.pathsep + native_dir
            os.environ[env_var] = new_env_string

    return new_env_string



def run_env_cmd(env_cmd: str, **opt):
    # this command returns the whole env variables after running the env_cmd, 
    # not just the changed ones.
    verbose = opt.get('verbose', 0)

    import tpsup.cmdtools
    sourced_env = {}

    # we cannot really run env cmd in the current shell, but we can run it in a subshell.
    # then we find out the effect of the cmd in the subshell, which is the change of
    # environment variables and values. we then update the current shell.

    # 1st, run the env_cmd in a subshell. Here we used bash as the subshell.
    # using bash as subshell requires us to use bash syntax.
    # but later the update to the current shell can be used by batch shell as well.
    cmd_stdout = tpsup.cmdtools.run_cmd_clean(
        # https://unix.stackexchange.com/questions/3510/
        # print only variables, not functions
        f"{env_cmd}; set -o posix; set", is_bash=True, **opt)
    
    # 2nd, parse the output of the subshell and find out what changed - the
    # difference between subshell's environment and current shell's environment.
    # if there is a difference, update the current shell's environment.
    for line in cmd_stdout.splitlines():
        # a variable is in form of key=value: no space before =. no space at front.
        if not line or re.match(r'^\s', line) or not re.search(r'=', line):
            continue

        # python partition vs split
        #   patition: split into 3 parts, the first part, the separator, and the rest
        #   split: split into n parts, each part is a string
        # (key, _, value) = line.partition("=")
        (key, value) = line.split("=", 1)  # split only at the first occurrence
        if not key:
            continue

        value2 = value.strip()
        # env value from windows is wrapped in single quotes. we need to remove it
        value2 = re.sub(r"^'", "", value2)
        value2 = re.sub(r"'$", "", value2)

        sourced_env[key] = value2 # this will be updated for certain conditions

        # don't touch BASH_SOURCE; otherwise, it makes sourced script's BASH_SOURCE not working.
        # better to leave all BASH_* and BASH* variables alone.
        if re.search(r'^BASH', key):
            if verbose > 1:
                print(f"skip {key}='{value2}' because changing BASH_SOURCE may break sourced script")
            continue
            # 'BASH_SOURCE' will be returned in sourced_env but not updated in os.environ

        if old_value := os.environ.get(key, None):
            if old_value == value2:
                if verbose > 1:
                    print(f"skip key={key} because old '{old_value}' == new '{value2}'")
                continue

            # if this is windows and value containing /, it is likely a path, then we need to convert
            # it to native path and compare it with the current environment variable value.
            if os.name == 'nt' and '/' in value2:
                try:
                    native_path = convert_path(value2, target_type='batch')
                except Exception as e:
                    if verbose:
                        print(f'failed to convert {key}={value2} to native path: {e}. skip converting')
                    native_path = value2
                if old_value == native_path:
                    if verbose > 1:
                        print(f"skip key={key} because old '{old_value}' == new '{native_path}' from '{value2}'")
                    continue
                value2 = native_path
        if verbose:
            print(f"overwrite {key}='{old_value}' with '{value2}'")
        
        try:
            os.environ[key] = value2
            #  ValueError: illegal environment variable name
        except ValueError as e:
            print(e)
            print(f"skip {key}='{value2}'")
            
        sourced_env[key] = value2
    return sourced_env

def source_env_file(file: str, **opt):
    # if not os.path.isfile(file):
    #     raise RuntimeError(f"file={file} does not exist")
    file2 = file.replace('\\', '/')

    if opt.get('verbose', 0):
        print(f"file2={file2}")

    return run_env_cmd(f"source {file2}", **opt)


def source_siteenv(SITESPEC: str = None, **opt):
    verbose = opt.get('verbose', 0)

    if SITESPEC is None:
        if not (SITESPEC := os.environ.get('SITESPEC', None)):
            raise RuntimeError(f"SITESPEC is not defined in environment")

    SITESPEC2 = SITESPEC.replace('\\', '/')

    print(f'SITESPEC2={SITESPEC2}')

    return source_env_file(f'{SITESPEC2}/profile', **opt)

def find_path_type(path: str, **opt):
    verbose = opt.get('verbose', 0)

    path = path.lower()

    if re.search(r'/cygdrive/', path):
        # /cygdrive/c/Program Files:/cygdrive/c/Users
        return 'cygwin'
    elif re.search(r'^/[a-z]/|:/[a-z]/|^/usr/bin|:/usr/bin', path):
        # /c/Program Files:/c/Users/tian/bin:/usr/bin
        return 'gitbash'
    elif re.search(r'^[a-z]:[/\\]|;[a-z]:[/\\]|^//[a-z]|;//[a-z]', path):
        # C:/Program Files;C:/Users;//server/share
        return 'batch'
    else:
        raise RuntimeError(f"cannot determine path type for path={path}")

def convert_path(source_path: str, is_env_var: bool = False, change_env: bool = False,
                 source_type: Literal['cygwin', 'gitbash', 'batch'] = None,
                 target_type: Literal['cygwin', 'gitbash', 'batch'] = None,
                 **opt):
    verbose = opt.get('verbose', 0)

    # source_path = source_path.replace('\\', '/')  # posix style
    if is_env_var:
        env_var = source_path
        if env_var in os.environ:
            source_path = os.environ[env_var]
        else:
            print(f"{env_var} is not an environment variable")
            return None

    if source_type is None:
        source_type = find_path_type(source_path, verbose=verbose)

    if verbose:
        print(f"source_type={source_type}")

    if target_type is None:
        myenv = Env()
        if term := myenv.term.get('term', None):
            if term in ('cygwin', 'gitbash', 'batch'):
                target_type = term

    if verbose:
        print(f"target_type={target_type}")

    if target_type is None:
        raise RuntimeError(
            f"cannot determine target_type from source_path={source_path}")
    
    delimiter = {
        'cygwin': ':',
        'gitbash': ':',
        'batch': ';'
    }

    if source_type == target_type:
        return source_path
        # no need to convert, no need to change environment variable

    pieces = source_path.split(delimiter[source_type]) # split by source delimiter
    if verbose >1:
        print(f"pieces={pformat(pieces)}")

    if source_type == 'cygwin':
        if target_type == 'batch':
            pieces2 = [re.sub(r'^/cygdrive/([a-z])/', r'\1:/', p)
                       for p in pieces]
        elif target_type == 'gitbash':
            pieces2 = [re.sub(r'^/cygdrive/([a-z])/', r'/\1/', p)
                       for p in pieces]
    elif source_type == 'gitbash':
        if target_type == 'batch':
            pieces2 = [re.sub(r'^/([a-z])/', r'\1:/',
                              p, re.IGNORECASE) for p in pieces]
        elif target_type == 'cygwin':
            pieces2 = [re.sub(r'^/([a-zA-Z])/',  r'/cygdrive/\1/', p)
                       for p in pieces]
    elif source_type == 'batch':
        # convert \ to /
        pieces2 = [p.replace('\\', '/') for p in pieces]
        if target_type == 'cygwin':
            # replace C:/Program Files with /cygdrive/c/Program Files, ignore case
            pieces2 = [re.sub(r'^([A-Z]):[/\\]', r'/cygdrive/\1/', p, flags=re.IGNORECASE)
                        for p in pieces2]
        elif target_type == 'gitbash':
            pieces2 = [re.sub(r'^([A-Z]):[/\\]', r'/\1/', p, flags=re.IGNORECASE)
                       for p in pieces2]
    if verbose > 1:
        print(f"pieces2={pformat(pieces2)}")
    
    target_path = delimiter[target_type].join(pieces2)

    if is_env_var and change_env:
        os.environ[env_var] = target_path

    return target_path


def get_native_path(path: str, **opt):
    myEnv = Env()
    if myEnv.isWindows:
        native_path = convert_path(path, target_type='batch')
    else:
        native_path = path
    return native_path

def get_term_type(**opt):
    # All the following depends on 'tpsup' env to set UNAME var in the environment.
    # This dependency should not be a concern because tpsup is always set in the environment
    # before we run tpsup scripts.
    # This is more relaible than Env().term['term'].
    # I used tpsup/python3/scripts/win_env to test this function.
    env_uname = os.environ.get('UNAME', None)
    if env_uname is None:
        raise RuntimeError("UNAME is not defined in environment")
    
    # UNAME=MINGW64_NT-10.0-19045 tianpc2 3.4.10-87d57229.x86_64 2024-02-14 20:17 UTC x86_64 Msys
    # UNAME=CYGWIN_NT-10.0-19045 tianpc2 3.5.3-1.x86_64 2024-04-03 17:25 UTC x86_64 Cygwin
    # UNAME=Linux tianpc2 5.15.167.4-microsoft-standard-WSL2 #1 SMP Tue Nov 5 00:21:55 UTC 2024 x86_64 x86_64 x86_64 GNU/Linux

    if re.search(r'MINGW64', env_uname):
        return 'gitbash'
    elif re.search(r'CYGWIN', env_uname):
        return 'cygwin'
    elif re.search(r'Linux', env_uname):
        return 'linux'
    elif re.search(r'Darwin', env_uname):
        return 'mac'
    else:
        env_os = os.environ.get('OS', None)
        if env_os is not None:
            if env_os == 'Windows_NT':
                return 'batch'
        raise RuntimeError(f"cannot determine term type from UNAME={env_uname}. run python3/scripts/win_env to test it")


def main():
    from tpsup.testtools import test_lines
    myenv = Env()
    myenv.adapt()  # don't block output in gitbash and cygwin

    tpsup = os.environ.get('TPSUP')
    tpsup_python3_scripts = os.path.join(tpsup, 'python3', 'scripts')

    def test_codes():
        myenv.__dict__

        # adjpath, normpath, and convert_path
        #     adjpath: convert / to \ on windows, and \ to / on linux
        #     normpath: convert /a/b/c to /a/b/c, a\b\c to a\b\c, C:/users/william to C:/users/william
        #     convert_path: convert /a/b/c to a:/b/c on windows, and a:/b/c to /a/b/c on linux

        myenv.adjpath("/a/b/c")
        myenv.adjpath(r"\a\b\c")
        os.path.normpath('/u/b/c')
        os.path.normpath(r'a\b\c')
        os.path.normpath('C:/users/william')
        print(f"native_url=file:///{os.path.normpath(os.environ.get('TPSUP'))}/scripts/tpslnm_test_input.html")

        get_tmp_dir()
        get_home_dir()
        get_user()
        get_user(secure=True)
        get_user_fullname(verbose=True)
        get_user_firstlast()

        path_contains(tpsup_python3_scripts)
        path_contains('python', regex=True)
        add_path(tpsup_python3_scripts)
        add_path("/junk/front", place='prepend')
        add_path("/junk/rear", place='append')


    # test_lines(test_codes, source_globals=globals(), source_locals=locals())
    test_lines(test_codes)

    print("")
    print("--------------------")
    print("test run_env_cmd()")
    print(f"before TEST_TIME={os.environ.get('TEST_TIME', None)}")
    run_env_cmd('export TEST_TIME=$(date +%H:%M:%S)',
                # verbose=2
                )
    print(f"after TEST_TIME={os.environ.get('TEST_TIME', None)}")

    print("")
    print("--------------------")
    print(f"before BASH_SOURCE={os.environ.get('BASH_SOURCE', None)}")
    source_env_file(f"$HOME/sitebase/github/tpsup/python3/lib/tpsup/cmdtools_test_bash_source.bash",
                verbose=1,
                   )
    print(f"after BASH_SOURCE={os.environ.get('BASH_SOURCE', None)}")

    print("")
    print("--------------------")
    print("test source_siteenv()")
    print(f"before TPSUP={os.environ.get('TPSUP', None)}")
    source_siteenv(f"{myenv.home_dir}/sitebase/github/site-spec",
                # verbose=2,
                   )
    
    # source_env_file(f"$HOME/sitebase/github/site-spec/profile",
    #             verbose=2,
    #                )
    # run_env_cmd(f"source $HOME/sitebase/github/site-spec/profile",
    #             verbose=2,
    #                )

    print(f"after TPSUP={os.environ.get('TPSUP', None)}")

    print("")
    print("--------------------")
    def test_code1():
        # from cygwin 
        convert_path('/cygdrive/c/Program Files:/cygdrive/c/users/tian/bin:/usr/bin', target_type='batch')
        convert_path('/cygdrive/c/Program Files:/cygdrive/c/users/tian/bin:/usr/bin', target_type='gitbash')
        convert_path('/cygdrive/c/Program Files:/cygdrive/c/users/tian/bin:/usr/bin', target_type='cygwin')

        # from batch
        convert_path(r'C:\Program Files;C:\Users\tian\bin;//myhost/bin', target_type='cygwin')
        convert_path(r'C:\Program Files;C:\Users\tian\bin;//myhost/bin', target_type='gitbash')
        convert_path(r'C:\Program Files;C:\Users\tian\bin;//myhost/bin', target_type='batch')

        # from gitbash
        convert_path('/c/Program Files:/c/users/tian/bin:/usr/bin', target_type='batch')
        convert_path('/c/Program Files:/c/users/tian/bin:/usr/bin', target_type='gitbash')
        convert_path('/c/Program Files:/c/users/tian/bin:/usr/bin', target_type='cygwin')

    test_lines(test_code1)

    if myenv.isWindows:
        def test_code2():
            convert_path('/cygdrive/c/Program Files', target_type='batch')
            convert_path('/cygdrive/c/Program Files', target_type='gitbash')
            convert_path('/cygdrive/c/Program Files', verbose=2)
            convert_path('TPSUP', is_env_var=True, change_env=True)

        test_lines(
            test_code2, source_globals=globals(), print_return=True, add_return=True)


if __name__ == "__main__":

    main()
