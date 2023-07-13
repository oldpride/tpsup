# mainly calling adb shell commands
import os
import tpsup.cmdtools
import tpsup.tptmp
from shutil import which

# steps to print android manifest file
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
# $ downloads # go to downloads directory
# $ adb pull /product/app/Gallery2/Gallery2.apk
# $ ls -l Gallery2.apk
# $ androidenv # add androidenv to your path
# $ apkanalyzer manifest print Gallery2.apk # print manifest file


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
    output = tpsup.cmdtools.run_cmd_clean(cmd, **opt)
    lines = output.splitlines()

    return lines


def adb_get_pkg_path(pkg: str, **opt):
    verbose = opt.get('verbose', 0)
    '''
    adb shell "pm path adb shell "pm path"
    '''
    cmd = f'adb shell "pm path {pkg}"'
    if verbose:
        print(f'cmd = {cmd}')
    output = tpsup.cmdtools.run_cmd_clean(cmd, **opt)

    lines = output.splitlines()
    # package:com.android.gallery3d
    path = lines[0].split(':')[1]

    # print detail
    cmd = f'adb shell "ls -l {path}"'
    if verbose:
        print(f'cmd = {cmd}')
    os.system(cmd)

    return path


def adb_pull(path: str, **opt):
    verbose = opt.get('verbose', 0)
    '''
    path can be a single file or dir, but no wild card.
    adb pull /product/app/Gallery2/Gallery2.apk
    '''

    # get basenmae of path
    path_basename = os.path.basename(path)

    if not (download_dir := opt.get('download_dir', None)):
        download_dir = tpsup.tptmp.get_dailydir()

    dest = f'{download_dir}/{path_basename}'
    if os.path.exists(dest):
        print(f'{dest} already exists. we use it')
        return dest
    else:
        print(f'{dest} does not exist. we will download it')

    cmd = f'adb pull {path} {download_dir}'
    if verbose:
        print(f'cmd = {cmd}')
    rc = os.system(cmd)
    print(f'rc = {rc}')

    if rc:
        raise Exception(f'failed to run {cmd}')

    cmd = f'ls -l {dest}'
    if verbose:
        print(f'cmd = {cmd}')
    os.system(cmd)

    return dest


def main():
    if adb_path := which('adb'):
        print(f"adb_path = {adb_path}")
    else:
        raise Exception("adb not found. run adroidenv")

    print(f"adb_find_pkg('gallery') = {adb_find_pkg('gallery')}")
    print("")
    print(
        f"adb_get_pkg_path('com.android.gallery3d') = {adb_get_pkg_path('com.android.gallery3d')}")
    print("")
    print(
        f"adb_pull('/product/app/Gallery2/Gallery2.apk') = {adb_pull('/product/app/Gallery2/Gallery2.apk')}")
    print("")


if __name__ == "__main__":
    main()
