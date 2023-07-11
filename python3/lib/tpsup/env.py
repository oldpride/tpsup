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


class Env:
    def __init__(self, **opt):
        self.verbose = opt.get("verbose", 0)
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

        if re.search("Windows", self.system, re.IGNORECASE):
            self.isWindows = True
            # >>> platform.uname()
            # uname_result(system='Windows', node='tianpc', release='10', version='10.0.19044', machine='AMD64')
            self.os_major, self.os_minor, *_ = self.uname.version.split('.')

            # this will be used by python.exe
            self.ls_cmd = "dir"
            # self.tmpdir = f"C:\\Users\\{os.environ['USERNAME']}\\AppData\\Local\\Temp"
            # self.home_dir = f"C:\\Users\\{os.environ['USERNAME']}"
            self.home_dir = f"C:\\Users\\{self.user}"
            self.tmpdir = f"{self.home_dir}\\AppData\\Local\\Temp"

            # this will be used by cygwin and gitbash terminals
            self.term = {}

            if os.environ.get("MSYSTEM", "") == "MINGW64":
                # GitBash signature
                # MSYSTEM=MINGW64
                self.isGitBash = True
                self.term['term'] = "gitbash"
                self.term['tmpdir'] = "/tmp"
                self.term['ls_cmd'] = "ls"
                self.term['/'] = subprocess.run(
                    ["cygpath", "-m", "/"], capture_output=True, text=True
                ).stdout.strip()  # bash/perl's backtick-equivalent
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
        else:
            raise RuntimeError(f"unsupported OS = {pformat(self.uname)}")

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


compiled_cyg_pattern = None
compiled_win_pattern = None


def cygpath(path: str, direction: Literal["win2cyg", "cyg2win"], **opt):
    # /cygdrive/c/Program Files;/cygdrive/c/Users;/cygdrive/d
    # c:/Program Files;c:/Users;d:
    if direction == "win2cyg":
        if opt.get("useRe", False):
            global compiled_win_pattern
            # use regex, which is not reliable as it can only
            # handle /cygdrive/..., but cannot convert /home/username
            if compiled_win_pattern is None:
                compiled_win_pattern = re.compile(r"(.):(.*)(;?)")
            path2 = compiled_win_pattern.sub(r"/cygdrive/\1/\2\3", path)
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
            global compiled_cyg_pattern
            if compiled_cyg_pattern is None:
                compiled_cyg_pattern = re.compile(r"/cygdrive/(.)(.*?)(;?)")

            path2 = compiled_cyg_pattern.sub(r"\1:\2\3", path)
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
    if not my_env.term.get('term', None) == 'gitbash':
        return paths

    new_paths = []
    for old_path in paths:
        new_path = old_path.replace(my_env.term['/'], '/')
        new_paths.append(new_path)
        if old_path != new_path:
            print(f"tpsup.env: restore_posix_paths: {old_path} -> {new_path}")
    return new_paths


def get_native_path(path: str, **opt) -> str:
    my_env = Env()
    if my_env.isCygwin or my_env.isGitBash:
        # when we run from cygwin, env var $TPSUP is /cygdrive/c/...
        # it is passed to windows program python.exe which doesn't
        # what to do with this path. therefore. we need to convert
        # from format like:
        #     /cygdrive/c/Program Files;/cygdrive/c/Users;/cygdrive/d
        # to
        #     c:/Program Files;c:/Users;d:
        # cygpath works in both cgywin and gitbash
        #
        new_path = cygpath(path, "cyg2win")
    else:
        new_path = path.replace("\\", "/")
    return new_path


def get_tmp_dir(**opt) -> str:
    return Env().tmpdir

# this is moved to tptmp.py
# def get_daily_tmp_dir(**opt) -> str:
#     env = Env()
#     tmpdir = env.tmpdir
#     user = env.user
#     today = datetime.datetime.now().strftime("%Y%m%d")
#     daily_tmp_dir = f"{tmpdir}/{user}/{today}"
#     if opt.get("create", False):
#         print(f"will create daily tmp dir {daily_tmp_dir}")
#         if not os.path.exists(daily_tmp_dir):
#             print(f"create daily tmp dir {daily_tmp_dir}")
#             os.makedirs(daily_tmp_dir)
#     return daily_tmp_dir


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
    elif env.isLinux:
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


def get_native_path(path: str, **opt) -> str:
    global re_split
    if re_split is None:
        re_split = re.compile(r'\\|/')
    components = re_split.split(path)
    print(f"components={components}")

    if path.startswith('/'):
        new_path = os.sep + os.path.join(*components)
    else:
        new_path = os.path.join(*components)
    return new_path


def path_contains(dir: str, **opt) -> bool:
    if not (env_string := opt.get('env_string', None)):
        env_var = opt.get('env_var', "PATH")
        env_string = os.environ.get(env_var)

    native_dir = get_native_path(dir)
    for p in env_string.split(os.pathsep):
        native_p = get_native_path(p)
        if native_p == native_dir:
            return True
    return False


def add_path(dir: str, **opt) -> str:
    verbose = opt.get('verbose', False)

    env_var = opt.get('env_var', "PATH")
    env_string = os.environ.get(env_var, '')
    if verbose:
        print(f"old {env_var}={env_string}")

    if opt.get('place', None) == 'prepend':
        paths = env_string.split(os.pathsep)
        if paths.length > 0 and paths[0] == dir:
            # already in the first place
            if verbose:
                print(f"dir={dir} is already in the first place of {env_var}")
            return
        else:
            new_paths = [dir] + [p for p in paths if p != dir]
            new_env_string = os.pathsep.join(new_paths)
            os.environ[env_var] = new_env_string
    elif opt.get('place', None) == 'append':
        paths = env_string.split(os.pathsep)
        if paths.length > 0 and paths[-1] == dir:
            # already in the last place
            if verbose:
                print(f"dir={dir} is already in the last place of {env_var}")
            return
        else:
            new_paths = [p for p in paths if p != dir] + [dir]
            new_env_string = os.pathsep.join(new_paths)
            os.environ[env_var] = new_env_string
    else:
        if path_contains(dir, **opt):
            if verbose:
                print(f"dir={dir} is already in {env_var}")
            return
        else:
            new_env_string = env_string + os.pathsep + dir
            os.environ[env_var] = new_env_string
    if verbose:
        print(f"new {env_var}={new_env_string}")


def main():
    myenv = Env()
    print(myenv)

    sys.stdout.flush()
    myenv.adapt()

    sys.stderr.write("1\n")
    time.sleep(2)
    sys.stderr.write("2\n")
    time.sleep(2)
    sys.stderr.write("3\n")

    for path in ("/a/b/c", r"\a\b\c"):
        print(
            f"converted path={path} to os standard path={myenv.adjpath(path)}")

    native_test_url = f"file:///{get_native_path(os.environ.get('TPSUP'))}/scripts/tpslnm_test_input.html"
    print(f"native_test_url = {native_test_url}")

    print(f"tmpdir = {get_tmp_dir()}")

    # print(f"query_user_fullname = {query_user_fullname(getpass.getuser())}")
    print(f"get_user_fullname = {get_user_fullname(verbose=True)}")
    print(f"get_user_firstlast = {get_user_firstlast()}")

    print(f"get_native_path('/u/b/c') = {get_native_path('/u/b/c')}")
    print("get_native_path(r'a\\b\\c')=" + get_native_path(r'a\b\c'))
    print("get_native_path('C:/users/william')=" +
          get_native_path('C:/users/william'))


if __name__ == "__main__":
    main()
