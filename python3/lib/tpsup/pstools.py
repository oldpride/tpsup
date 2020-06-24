import tpsup.env
import sys
import os


def ps_grep_basename(basename: str, **opt):
    verbose = opt.get('verbose', 0)

    if verbose:
        sys.stderr.write(f'Find any running {basename}\n')

    env = opt.get('env', None)

    if env is None:
        env = tpsup.env.Env()

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
    ps_grep_basename('pycharm', verbose=1)


if __name__ == '__main__':
    main()
