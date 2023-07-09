from pprint import pformat
import re
import subprocess
import tpsup.env


def run_cmd(cmd: str, **opt):
    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'cmd = {cmd}')

    is_bash = opt.get('is_bash', False)

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
    myenv = tpsup.env.Env()
    if myenv.isWindows:
        if is_bash:
            bash = 'C:/Windows/System32/bash.exe'

            # two possible solutions:
            # 1. tried this, but not working
            #   extra_opt['executable'] = bash
            #   cmd2 = cmd

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
    return_type = opt.get('return_type', 'split')
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
    else:
        raise RuntimeError(f"unsupported return_type={return_type}")

    return ret


def run_cmd2(cmd: str, **opt):
    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'cmd = {cmd}')

    # extra_opt = {}
    # myenv = tpsup.env.Env()
    # if myenv.isWindows:
    #     bash = 'C:/Windows/System32/bash.exe'
    # else:
    #     bash = '/bin/bash'
    # extra_opt['executable'] = bash
    # print(f'extra_opt = {extra_opt}')

    # https://code-maven.com/qx-in-python
    proc = subprocess.Popen(cmd,
                            shell=True,  # this allows to run multiple commands
                            # executable='/bin/bash',
                            # executable='C:/Windows/System32/bash.exe',
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            # **extra_opt,
                            )
    stdout, stderr = proc.communicate()

    return {
        'rc': proc.returncode,
        'stdout': stdout.decode(),
        'stderr': stderr.decode(),
    }


def run_bash(cmd: str, **opt):
    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'cmd = {cmd}')

    myenv = tpsup.env.Env()
    if myenv.isWindows:
        bash = 'C:/Windows/System32/bash.exe'
    else:
        bash = '/bin/bash'
    # https://stackoverflow.com/questions/17742789/running-multiple-bash-commands-with-subprocess
    proc = subprocess.run([bash, '-c', cmd],
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          )
    # stdout, stderr = proc.communicate(cmd + '\n')

    return {
        'rc': proc.returncode,
        'stdout': proc.stdout.decode(),
        'stderr': proc.stderr.decode(),
    }


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
        # print(
        #     f"run_cmd('{cmd}', is_bash=True, return_type='combined') = {pformat(run_cmd(cmd, is_bash=True, return_type='combined'))}")
        # # print(f"run_cmd2('{cmd}') = {run_cmd2(cmd)}")
        # print(
        #     f"run_bash('{cmd}', is_bash=True) = {pformat(run_bash(cmd, is_bash=True))}")
        print('')


if __name__ == "__main__":
    main()
