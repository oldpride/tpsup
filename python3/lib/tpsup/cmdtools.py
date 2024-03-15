import os
from pprint import pformat
import re
import subprocess
import sys
import tpsup.envtools


def run_cmd(cmd: str, is_bash=False, bash_exe='gitbash', return_type='split', print_output=0, **opt):
    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'cmd = {cmd}')

    # on windows, default shell is batch.
    # on linux, default shell is /bin/sh.

    # when calling bash.exe, $ needs to be escaped.
    # on PC, python calling bash.exe in this way.
    # C:\Users\william>C:/Windows/System32/bash.exe -c "var1=abc; [[ \$var1 =~ ^a ]] && echo \$?"
    # 0
    'var1=abc; [[ \$var1 =~ ^a ]] && echo yes; [[ \$var1 =~ ^b ]]; echo \$?',

    # when calling inside gitbash terminal or linux terminal, no need to escape $
    # (win10-python3.10) william@tianpc2:/c/Users/william$ bash -c 'var1=abc; [[ $var1 =~ ^a ]] && echo yes; [[ $var1 =~ ^b ]]; echo $?'
    # yes
    # 1

    extra_opt = {}
    myenv = tpsup.envtools.Env()
    if myenv.isWindows:
        if is_bash:
            if bash_exe == 'wsl':
                bash = 'C:/Windows/System32/bash.exe'  # this is WSL bash
                # wsl has its complete subsystem, for example, totally separate
                # installations.
                # for example, java is /usr/lib/jvm/java-11-openjdk-amd64/bin/java.
                # $ uname -a
                # Linux tianpc2 5.15.90.1-microsoft-standard-WSL2 ... 2023 x86_64 x86_64 x86_64 GNU/Linux
            elif bash_exe == 'gitbash':
                bash = 'C:/Program Files/Git/bin/bash.exe'  # this is gitbash's bash
                # gitbash mainly uses windows native software,
                # for example, java is /c/Program Files/Java/jdk1.8.0_202/bin/java
            else:
                bash = bash_exe

            # two possible solutions:
            # 1. tried this, but not working
            #    extra_opt['executable'] = bash
            #    cmd2 = cmd
            # failed with error
            #    RuntimeError: cmd=... failed with rc=126, stderr=/c: /c: Is a directory

            # 2. this works
            cmd3 = re.sub(r'\$', '\\$', cmd)  # escape $ for bash.exe
            cmd2 = [bash, '-c', cmd3]
        else:
            cmd2 = cmd
    else:
        # for linux, default shell is /bin/sh, not bash.
        cmd2 = cmd
        if is_bash:
            bash = '/bin/bash'
            extra_opt['executable'] = bash

    if verbose:
        print(f'cmd2 = {cmd2}')
        print(f'extra_opt = {extra_opt}')

    # https://docs.python.org/3/library/subprocess.html
    # If capture_output is true, stdout and stderr will be captured.
    #    When used, the internal Popen object is automatically created with stdout=PIPE and stderr=PIPE.
    # The stdout and stderr arguments may not be supplied at the same time as capture_output.
    # If you wish to capture and combine both streams into one,
    #    use stdout=PIPE and stderr=STDOUT instead of capture_output.
    if return_type == 'split':
        proc = subprocess.run(cmd2,
                              shell=True,  # this allows to run multiple commands
                              capture_output=True,
                              text=True,
                              **extra_opt,)
        ret = {
            'rc': proc.returncode,
            'stdout': proc.stdout,
            'stderr': proc.stderr,
        }

        if print_output:
            print(ret['stdout'])
            print(ret['stderr'], file=sys.stderr)
    elif return_type == 'combined':
        proc = subprocess.run(cmd2,
                              shell=True,  # this allows to run multiple commands
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              text=True,
                              **extra_opt,)
        ret = {
            'rc': proc.returncode,
            'combined': proc.stdout
        }
        if print_output:
            print(ret['combined'])
    else:
        raise RuntimeError(f"unsupported return_type={return_type}")

    return ret


def run_cmd_clean(cmd: str, **opt):
    ret = run_cmd(cmd, **opt)
    if ret['rc'] != 0:
        raise RuntimeError(
            f"cmd={cmd} failed with rc={ret['rc']}, stderr={ret['stderr']}")
    elif ret['stderr']:
        print(ret['stderr'])
        # raise RuntimeError(f"cmd={cmd} failed with stderr={ret['stderr']}")
    return ret['stdout']


def is_exe(fpath, **opt):
    verbose = opt.get('verbose', 0)
    if not os.path.exists(fpath):
        if verbose > 1:
            print(f'fpath={fpath} does not exist', file=sys.stderr)
        return False

    if not os.access(fpath, os.X_OK):
        if verbose > 1:
            print(f'fpath={fpath} has no access', file=sys.stderr)
        return False

    if not os.path.isfile(fpath):
        if verbose > 1:
            print(f'fpath={fpath} is not a file', file=sys.stderr)
        return False

    return True

# https://stackoverflow.com/questions/377017
# search for extensions too


def which(program, **opt):
    verbose = opt.get('verbose', 0)

    def ext_candidates(fpath):
        yield fpath
        for ext in os.environ.get("PATHEXT", "").split(os.pathsep):
            yield fpath + ext

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            for candidate in ext_candidates(exe_file):
                if is_exe(candidate, verbose=verbose):
                    return candidate

    return None


def main():
    print("Heads up! on windows, the default shell is cmd.exe, not bash.")
    print("")

    for cmd in [
        'echo "first"; echo "second"',
        'echo "hello stdout"',
        'echo "hello stderr" >&2',
        'echo a | grep a',
        'ls /no_such_file',
        'echo \$HOME',
        'var1=abc; [[ $var1 =~ ^a ]] && echo yes; [[ $var1 =~ ^b ]]; echo $?',
    ]:
        print(
            f"run_cmd('{cmd}', is_bash=True) = {pformat(run_cmd(cmd, is_bash=True))}")
        print('')

    import tpsup.androidtools
    import shutil
    tpsup.androidtools.set_android_env()
    print("")
    print(f"compare two ways of which(). shutil.which() cannot find bash in windows!!!")
    print(
        f"tpsup.cmdtools.which('apkanalyzer') = {which('apkanalyzer')}")
    print(f"shutil.which('apkanalyzer') = {shutil.which('apkanalyzer')}")
    print("")

    # keep test code in a function so that IDE can check syntax

    def test_code():
        # from tpsup.cmdtools import run_cmd
        # bash script on windows must run with bash.exe
        # apkanalyzer is a bash script
        run_cmd('apkanalyzer --version', is_bash=True, print=1)

        run_cmd('which java', is_bash=True, print=1)
        run_cmd('which java', is_bash=True, print=1, bash_exe='wsl')
    from tpsup.testtools import test_lines
    # we import it here because this is for test only

    test_lines(test_code, source_globals=globals())
    # we pass globals() so that test_code can see our functions, eg, run_cmd()

    import tpsup.tmptools
    tmpdir = tpsup.tmptools.get_dailydir()
    tmpfile = f'{tmpdir}/test.txt'
    with open(tmpfile, 'w') as fh:
        fh.write("hello world\n")


if __name__ == "__main__":
    main()
