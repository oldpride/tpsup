import subprocess
import tpsup.env


def run_cmd(cmd: str, **opt):
    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'cmd = {cmd}')

    # https://docs.python.org/3/library/subprocess.html
    # If capture_output is true, stdout and stderr will be captured.
    #    When used, the internal Popen object is automatically created with stdout=PIPE and stderr=PIPE.
    # The stdout and stderr arguments may not be supplied at the same time as capture_output.
    # If you wish to capture and combine both streams into one,
    #    use stdout=PIPE and stderr=STDOUT instead of capture_output.
    return_type = opt.get('return_type', 'split')
    if return_type.startswith('split'):
        proc = subprocess.run(cmd,
                              shell=True,  # this allows to run multiple commands
                              capture_output=True, text=True)
        if return_type == 'split.lines':
            ret = {
                'rc': proc.returncode,
                'stdout': proc.stdout.split('\n'),
                'stderr': proc.stderr.split('\n'),
            }
        elif return_type == 'split':
            ret = {
                'rc': proc.returncode,
                'stdout': proc.stdout,
                'stderr': proc.stderr,
            }
        else:
            raise RuntimeError(f"unsupported return_type={return_type}")
    elif return_type.startswith('combined'):
        proc = subprocess.run(cmd,
                              shell=True,  # this allows to run multiple commands
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True)
        if return_type == 'combined.lines':
            ret = {
                'rc': proc.returncode,
                'combined': proc.stdout.split('\n')
            }
        elif return_type == 'combined':
            ret = {
                'rc': proc.returncode,
                'combined': proc.stdout
            }
        else:
            raise RuntimeError(f"unsupported return_type={return_type}")
    else:
        raise RuntimeError(f"unsupported return_type={return_type}")

    return ret


def run_cmd2(cmd: str, **opt):
    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'cmd = {cmd}')

    # https://code-maven.com/qx-in-python
    proc = subprocess.Popen(cmd,
                            shell=True,  # this allows to run multiple commands
                            # executable='/bin/bash',
                            # executable='C:/Windows/System32/bash.exe',
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
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
    for cmd in [
        # 'adb shell pm list "packages|grep gallery"',
        # 'adb shell pm list packages|grep com.android.w',
        'echo "first"; echo "second"',
        'echo "hello stdout"',
        'echo "hello stderr" >&2',
        'echo a | grep a',
        'ls /no_such_file',
        'echo $HOME',

        # C:\Users\william>C:/Windows/System32/bash.exe -c "var1=abc; [[ \$var1 =~ ^a ]] && echo \$?"
        # 0
        'var1=abc; [[ \$var1 =~ ^a ]] && echo yes; [[ \$var1 =~ ^b ]]; echo \$?',

    ]:
        print(f"run_cmd('{cmd}') = {run_cmd(cmd)}")
        print(
            f"run_cmd('{cmd}', return_type='combined') = {run_cmd(cmd, return_type='combined')}")
        print(f"run_cmd2('{cmd}') = {run_cmd2(cmd)}")
        print(f"run_bash('{cmd}') = {run_bash(cmd)}")
        print('')


if __name__ == "__main__":
    main()
