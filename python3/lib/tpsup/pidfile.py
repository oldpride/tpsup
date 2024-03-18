import os
import getpass
import platform
import tpsup.pstools


class pidfile:
    def __init__(self, prog: str, dir: str = None, ):
        prog = os.path.basename(prog)
        parts = prog.split('.')
        self.prog = parts[0]

        if dir is None:
            self.dir = os.path.expanduser("~")
        else:
            self.dir = dir

        self.hostname = platform.node().split('.')[0]
        # os.getlogin() stopped working
        # self.user = os.getlogin()
        self.user = getpass.getuser()

        self.pid = os.getpid()
        pidfile = os.path.join(self.dir, f"{self.user}_{self.hostname}_{self.prog}.txt")

        self.pidfile = None
        if os.path.isfile(pidfile):
            # if the file exists, the first line should be pid
            with open(pidfile, 'r') as f:
                old_pid = f.readline()
                # check whether this pid is still running
                if old_pid:
                    old_pid = int(old_pid)

                    if tpsup.pstools.pid_alive(old_pid):
                        raise RuntimeError(f"{pidfile} already exists with an live pid={old_pid}")
                    else:
                        print(f"{pidfile} already exists but inside pid={old_pid} is not alive. we will overwrite it")
        with open(pidfile, 'w') as f:
            print(f"{self.pid}", file=f)
        self.pidfile = pidfile

    def __enter__(self):
        return self.pidfile

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.remove()

    def remove(self):
        if self.pidfile:
            pidfile = self.pidfile
            self.pidfile = None
            os.unlink(pidfile)


def main():
    import tpsup.envtools
    myenv = tpsup.envtools.Env()

    print(f"\n---------- this should work -------------")
    test_pid = 12345
    test_pidfile = os.path.join(myenv.home_dir, f"{myenv.user}_{myenv.hostname.split('.')[0]}_test.txt")

    with open(test_pidfile, 'w') as f:
        print(f"{test_pid}", file=f)

    with pidfile('test') as pf:
        myenv.ls(pf)
        with open(pf, 'r') as f:
            print(f.readline())

    print(f"\n---------- this should fail -------------")
    test_pid = os.getpid()
    with open(test_pidfile, 'w') as f:
        print(f"{test_pid}", file=f)

    with pidfile('test') as pf:
        myenv.ls(pf)


if __name__ == '__main__':
    main()
