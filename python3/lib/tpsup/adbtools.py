# to test with emulator
# $ siteenv
# $ p3env
# $ svenv
# $ appium_emulator.bash start
# $ adb shell pm list packages |grep com.android.gallery3d
#   package:com.android.gallery3d
# $ adb shell pm path  com.android.gallery3d
#   package:/product/app/Gallery2/Gallery2.apk
# $ adb shell "ls -l /product/app/Gallery2/Gallery2.apk"
#   -rw-r--r-- 1 root root 7486427 2021-03-08 17:14 /product/app/Gallery2/Gallery2.apk

import shlex
import subprocess


def adb_find_pkg(pattern: str, **opt):
    verbose = opt.get('verbose', 0)
    '''
    find package name
    adb shell "pm list packages|grep test02"
    i got "package:org.nativescript.test02ngchallenge"
    this info can also be found in package source code
    '''
    cmd = f'adb shell "pm list packages|grep {pattern}"'
    if verbose:
        print(f'cmd = {cmd}')
    # get output from command
    lines = subprocess.run(shlex.split(
        cmd), capture_output=True, text=True).stdout.strip().split('\n')
    return lines


def main():
    print(f"adb_find_pkg('gallery') = {adb_find_pkg('gallery')}")


if __name__ == "__main__":
    main()
