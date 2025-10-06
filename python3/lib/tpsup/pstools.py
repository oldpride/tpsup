import tpsup.envtools
import sys
import os
import subprocess
import platform
import re


def ps_grep(pattern, printOutput=1, env=None, verbose=0):
    if verbose:
        sys.stderr.write(f'Find any running {pattern}\n')

    if env is None:
        env = tpsup.envtools.get_env()

    # "ps -ef" in GitBash and Cygwin can only see its own processes
    # if env.isLinux or env.isGitBash or env.isCygwin:
    if env.isLinux or env.isDarwin:
        # cmd = f'ps -ef | grep -i {pattern} | grep -v grep'
        cmd = f'ps -ef'
    elif env.isWindows:
        # tasklist doesn't support regex
        # cmd = f'tasklist /fi "Imagename eq {pattern}*"'

        # this is slow, taking about 20 seconds
        # cmd = f'tasklist /v /fo csv'

        # this is fast, taking about 1 second
        # cmd = 'PowerShell -command "get-process"'

        # this is the best, giving command line args too and is fast

        cmd = 'PowerShell -command "(Get-CimInstance -ClassName Win32_Process|Select-object -property CreationDate,ProcessId,CommandLIne| Out-String -Stream -Width 1000).Trim()"'
    else:
        raise RuntimeError(f"unsupported os {env.uname}")

    if verbose:
        env.adapt()
        sys.stderr.write(f"{cmd}\n")

    # https://stackoverflow.com/questions/7787120/check-if-a-process-is-running-or-not-on-windows
    # https://stackoverflow.com/questions/13332268/how-to-use-subprocess-command-with-pipes

    # output = subprocess.check_output(cmdArray).decode()
    ps = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = ps.communicate()[0].decode()

    # if printOutput:
    #     print(output)

    # # check in last line for process name
    # last_line = output.strip().split('\r\n')[-1]
    # if env.isLinux:
    #     return last_line.lower().find(basename.lower()) != -1
    # else:
    #     # because Fail message could be translated
    #     return last_line.lower().startswith(pattern.lower())

    # pattern match
    matched_lines = []
    for line in (output.strip().split('\r\n')):
        if re.search(pattern, line, re.IGNORECASE):
            matched_lines.append(line)

    if printOutput:
        for line in matched_lines:
            print(line)

    return matched_lines


def pid_alive(pid: int):
    """ Check For whether a pid is alive """

    system = platform.uname().system
    if re.search('Linux', system, re.IGNORECASE):
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        else:
            return True
    elif re.search('Windows', system, re.IGNORECASE):
        out = subprocess.check_output(
            ["tasklist", "/fi", f"PID eq {pid}"]).strip()
        # b'INFO: No tasks are running which match the specified criteria.'

        if re.search(b'No tasks', out, re.IGNORECASE):
            return False
        else:
            return True
    else:
        raise RuntimeError(f"unsupported system={system}")

def kill_procs(procs: list, **opt):
    for proc in procs:
        print(f"kill {proc}")
        my_env = tpsup.envtools.get_env()
        if my_env.isWindows:
            # cmd = f"taskkill /f /im {proc}"
            cmd = f"pkill {proc}"
        else:
            # -f means full command line
            cmd = f"pkill -f -- {proc}"
        print(f"cmd={cmd}")
        os.system(cmd)

def check_procs(procs: list, kill=False, **opt) -> list:
    running_procs = []
    for proc in procs:
        print(f"check whether {proc} is running")
        if tpsup.pstools.ps_grep(f"{proc}", printOutput=1):
            print(f"{proc} is running\n")
            running_procs.append(proc)
            # default not to kill it because it takes time to start up
            if kill:
                kill_procs([proc], **opt)
        else:
            print(f"{proc} is NOT running\n")

    return running_procs

def main():

    good_pid = os.getpid()
    bad_pid = 1111111

    def test_codes():
        pid_alive(good_pid)
        pid_alive(bad_pid)
        ps_grep("code.exe|pycharm")

    from tpsup.testtools import test_lines
    test_lines(test_codes, source_globals=globals(), source_locals=locals())


if __name__ == '__main__':
    main()
