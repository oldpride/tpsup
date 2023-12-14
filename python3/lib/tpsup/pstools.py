import tpsup.envtools
import sys
import os
import subprocess
import platform
import re


def prog_running(basename, printOutput=0,  verbose=0):
    if verbose:
        sys.stderr.write(f'Find any running {basename}\n')

    env = tpsup.envtools.Env()

    # "ps -ef" in GitBash and Cygwin can only see its own processes
    # if env.isLinux or env.isGitBash or env.isCygwin:
    if env.isLinux:
        cmd = f'ps -ef | grep -i {basename} | grep -v grep'
    elif env.isWindows:
        cmd = f'tasklist /fi "Imagename eq {basename}*"'
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

    if printOutput:
        print(output)

    # check in last line for process name
    last_line = output.strip().split('\r\n')[-1]

    if env.isLinux:
        return last_line.lower().find(basename.lower()) != -1
    else:
        # because Fail message could be translated
        return last_line.lower().startswith(basename.lower())


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


def ps_grep_basename(basename: str, **opt):
    verbose = opt.get('verbose', 0)

    if verbose:
        sys.stderr.write(f'Find any running {basename}\n')

    env = opt.get('env', None)

    if env is None:
        env = tpsup.envtools.Env()

    # "ps -ef" in GitBash and Cygwin can only see its own processes
    # if env.isLinux or env.isGitBash or env.isCygwin:
    if env.isLinux:
        cmd = f'ps -ef|grep -i {basename}|grep -v grep'
    elif env.isWindows:
        cmd = f'tasklist /fi "Imagename eq {basename}*"'
    else:
        raise RuntimeError(f"unsupported os {env.uname}")

    if verbose:
        env.adapt()
        sys.stderr.write(f"{cmd}\n")
    os.system(cmd)


def main():
    # print("--------- test ps_grep_basename() -----------------")
    # ps_grep_basename('pycharm', verbose=1)

    # print("--------- test pid_alive() -----------------")
    # good_pid = os.getpid()
    # if pid_alive(good_pid):
    #     print(f"OK:    good_pid={good_pid} is alive")
    # else:
    #     print(f"ERROR: good_pid={good_pid} is NOT alive")

    # bad_pid = 1111111
    # if not pid_alive(bad_pid):
    #     print(f"OK:    bad_pid={bad_pid} is NOT alive")
    # else:
    #     print(f"ERROR: bad_pid={bad_pid} is alive")

    # test = f'prog_running("chrome", printOutput=1)'
    # print(f'---- test {test} -----')
    # print(f'result={eval(test)}')

    good_pid = os.getpid()
    bad_pid = 1111111

    def test_codes():
        ps_grep_basename('pycharm', verbose=1)
        pid_alive(good_pid)
        pid_alive(bad_pid)
        prog_running("chrome", printOutput=1)

    from tpsup.exectools import test_lines
    test_lines(test_codes, source_globals=globals(), source_locals=locals())


if __name__ == '__main__':
    main()
