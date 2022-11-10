import os
import shutil
import time

import tpsup.env
from time import strftime, localtime

class tptmp:
    def __init__(self, retention_day: int = 7, retention_sec: int = None, base: str = None,
                 suffix:str = '', verbose: int = 0):
        """
        we don't but **kwargs because we want to catch wrong params, in particular, retention_day and retention_sec
        :param retention_day:
        :param retention_sec:
        :param base:
        :param verbose:
        """
        self.verbose = verbose
        self.suffix = suffix

        if retention_sec is not None:
            self.retention_sec = retention_sec
        else:
            self.retention_sec = retention_day * 24 * 60 * 60  # convert day to seconds

        self.base = base
        if not self.base:
            env = tpsup.env.Env()
            if env.isLinux:
                self.base = os.path.join(env.tmpdir, f"tmp_{env.user}")
            else:
                self.base = os.path.join(env.tmpdir, f"daily")

        yyyymmdd = strftime("%Y%m%d", localtime())
        self.dailydir = os.path.join(self.base, yyyymmdd)

    def get_dailydir(self, **opt):
        if not os.path.exists(self.dailydir):
            if opt.get('mkdir_now', 1):
                os.makedirs(self.dailydir, exist_ok=True)  # mkdir -p
                # whenever we make new dailydir also clean old dailydir
                self.clean_old_tmpdir()
        return self.dailydir

    def get_nowdir(self, suffix:str = '', **opt):
        dailydir = self.get_dailydir()
        HHMMSS = strftime("%H%M%S", localtime())

        if not suffix:
            suffix = self.suffix

        if suffix:
            nowdir = os.path.join(dailydir, f"{HHMMSS}_{suffix}")
        else:
            nowdir = os.path.join(dailydir, HHMMSS)

        if opt.get('mkdir_now', 1):
            os.makedirs(nowdir, exist_ok=True)
        return nowdir

    def clean_old_tmpdir(self, retention_day: int = None, retention_sec: int = None, dryrun: bool=False, verbose: int = 0):
        if retention_sec is None:
            if retention_day is None:
                retention_sec = self.retention_sec
            else:
                retention_sec = retention_day * 24 * 60 * 60  # convert day to seconds
        # else use retention_sec

        base = self.base
        print(f"base={base}")
        now = time.time()
        for f in os.listdir(base):
            fullname = os.path.join(base, f)
            mtime = os.stat(fullname).st_mtime
            # print(f"{fullname}: mtime={mtime} vs now-retention_sec={now}-{retention_sec}")
            if mtime < now - retention_sec:
                if dryrun:
                    print(f"dryrun: removing {fullname}")
                else:
                    print(f"removing {fullname}")
                    # shutil.rmtree(fullname)

def main():
    mytmp = tptmp()
    print(f"nowdir={mytmp.get_nowdir(suffix='test')}")
    time.sleep(1)
    print(f"nowdir={mytmp.get_nowdir(suffix='test')}")
    time.sleep(1)
    mytmp.clean_old_tmpdir(retention_sec=1, dryrun=True, verbose=1)

    tpsup.env.Env().ls(mytmp.get_dailydir())

if __name__ == '__main__':
    main()
