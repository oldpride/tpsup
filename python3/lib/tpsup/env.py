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
            if os.environ.get("MSYSTEM", "") == "MINGW64":
                # GitBash signature
                # MSYSTEM=MINGW64
                self.isGitBash = True
                self.tmpdir = "/tmp"
            elif "MINTTY_SHORTCUT" in os.environ:
                # Cygwin signature:
                # MINTTY_SHORTCUT=/cygdrive/c/Users/william/AppData/Roaming/Microsoft/Internet
                #  Explorer/Quick Launch/User Pinned/TaskBar/Cygwin64 Terminal.lnk
                # see https://mintty.github.io/mintty.1.html
                #   "sets environment variable MINTTY_SHORTCUT"
                self.isCygwin = True
                self.tmpdir = "/tmp"
                # because cygwin's home dir is C:\cygwin64\home\<username>, likely not the normal windows's home
                # dir C:/users/<username>. use C:/users/<username> instead
                self.home_dir = f'C:/Users/{os.environ["USERNAME"]}'
            else:
                self.ls_cmd = "dir"
                self.tmpdir = (
                    f"C:\\Users\\{os.environ['USERNAME']}\\AppData\\Local\\Temp"
                )
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
        os.system(f"{self.ls_cmd} {self.adjpath(path)}")


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


def get_user_fullname(user: str = None, **opt) -> str:
    verbose = opt.get('verbose', False)

    user = opt.get('user', None)
    if user is None:
        user = getpass.getuser()

    full_name = None
    env = Env()
    if env.isWindows:
        # cmd = 'wmic useraccount where name="william" get fullname /value'
        cmd = 'wmic useraccount where name="%username%" get fullname /value'
        cmd = cmd.replace('%username%', user)

        if verbose:
            print(f"cmd={cmd}")

        ps = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = ps.communicate()[0].decode()
        if verbose:
            print(f"output='{output}'")

        # Extract the full name from the output
        full_name = output.strip().split('=')[1]
    elif env.isLinux:
        # only available in linux, not windows. therefore, we need to put it here.
        import pwd
        full_name = pwd.getpwnam(getpass.getuser()).pw_gecos.split(',')[0]
    else:
        raise RuntimeError(f"unsupported OS = {env.uname}")
    return full_name


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
    print(f"user full name = {get_user_fullname()}")


if __name__ == "__main__":
    main()
