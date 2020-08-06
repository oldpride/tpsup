import functools
import os
import platform
import re
import sys
import time


def flush_rightaway(func):
    @functools.wraps(func)
    def flushed(*args, **kwargs):
        result = func(*args, **kwargs)
        sys.stderr.flush()
        return result
    return flushed


class Env:
    def __init__(self, **opt):
        self.verbose = opt.get('verbose', 0)
        self.uname = platform.uname()
        self.system = self.uname.system
        self.home_dir = os.path.expanduser("~")
        self.isGitBash = False
        self.isCygwin = False
        self.isLinux = False
        self.isWindows = False
        self.environ = os.environ
        self.PATH = os.environ.get('PATH', '')
        self.python_version = platform.python_version()
        self.ls = 'ls'

        if re.search("Windows", self.system, re.IGNORECASE):
            self.isWindows = True
            if os.environ.get('MSYSTEM', '') == 'MINGW64':
                # GitBash signature
                # MSYSTEM=MINGW64
                self.isGitBash = True
            elif re.search('cygdrive|cygwin', self.PATH, re.IGNORECASE):
                # Cygwin signature: /cygdrive/c/... in PATH PATH=/cygdrive/c/Program Files (x86)/Common
                # Files/Oracle/Java/javapath:/cygdrive/c/Program Files/Python37/Scripts:...
                self.isCygwin = True

                # because cygwin's home dir is C:\cygwin64\home\<username>, likely not the normal windows's home
                # dir C:/users/<username>. use C:/users/<username> instead
                self.home_dir = f'C:/Users/{os.environ["USER"]}'
            else:
                self.ls = 'dir'
        if re.search("Linux", self.system, re.IGNORECASE):
            self.isLinux = True

    def __str__(self):
        strings = []
        for attr in sorted(self.__dict__):
            strings.append(f'{attr} = {self.__dict__[attr]}')
        return '\n'.join(strings)

    def adapt(self):
        if self.isCygwin or self.isGitBash:
            # https://stackoverflow.com/questions/34668972/cmd-and-git-bash-have-a-different-result-when-run-a-python-code
            # overwrite the standard function
            sys.stderr.write = flush_rightaway(sys.stderr.write)


def main():
    myenv = Env()
    print(myenv)

    sys.stdout.flush()
    myenv.adapt()

    sys.stderr.write("1\n")
    time.sleep(2);
    sys.stderr.write("2\n")
    time.sleep(2);
    sys.stderr.write("3\n")


if __name__ == '__main__':
    main()
