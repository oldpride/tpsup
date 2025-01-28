# mainly calling adb shell commands
import os
import time
import tpsup.cmdtools
import tpsup.tmptools
from shutil import which
from tpsup.envtools import get_home_dir

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
    pkgs = []
    for line in lines:
        if line.startswith('package:'):
            pkgs.append(line.replace('package:', ''))

    return pkgs


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
    # package:com.android.photos

    if verbose:
        print(f'{lines}')

    if len(lines) > 1:
        print(f'multiple package path found for {pkg}: we use the first one')
    elif len(lines) == 0:
        raise Exception(f'no package path found for {pkg}')
    
    path = lines[0].split(':')[1]

    # print detail
    cmd = f'adb shell "ls -l {path}"'
    if verbose:
        print(f'cmd = {cmd}')
    os.system(cmd)

    return path


def adb_pull(path: str, dest:str = None, **opt):
    verbose = opt.get('verbose', 0)
    '''
    path can be a single file or dir, but no wild card.
    adb pull /product/app/Gallery2/Gallery2.apk
    '''

    download_dir = opt.get('download_dir', None)
    if not download_dir:
        download_dir = tpsup.tmptools.get_dailydir()

    path_basename = os.path.basename(path)        

    download_full_path = f'{download_dir}/{path_basename}'.replace('\\', '/')

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

    if dest and download_full_path != dest:
        os.rename(download_full_path, dest)
    return dest

def adb_pull_pkg(pkg_pattern: str, **opt):
    verbose = opt.get('verbose', 0)
    '''
    1. find package name, adb_find_pkg
    2. get package path, adb_get_pkg_path
    3. pull the package, adb_pull
    '''
    pkgs = adb_find_pkg(pkg_pattern, **opt)
    if len(pkgs) == 0:
        raise Exception(f'no package found for {pkg_pattern}')
    elif len(pkgs) > 1:
        raise Exception(f'multiple packages matched {pkg_pattern}: {pkgs}')
    else:
        pkg = pkgs[0]

    print(f'pkg = {pkg}')

    # get package path
    device_path = adb_get_pkg_path(pkg, **opt)

    download_dir = opt.get('download_dir', None)
    if not download_dir:
        download_dir = tpsup.tmptools.get_dailydir()

    dest = f'{download_dir}/{pkg}.apk'.replace('\\', '/')

    adb_pull(device_path, dest, **opt)

    return dest



def adb_wait_screen(until: str, 
                    check_interval: int = 5, 
                    timeout: int = 3600, **opt):
    '''
    use adb screencap to check whether screen is still for a while.
    we use homedir/downloads folder as default folder to save the screenshots
    '''
    verbose = opt.get('verbose', 0)

    if not (until == 'still' or until == 'moving'):
        raise Exception(f"unknown until={until}; can only be 'still' or 'moving'")
    
    homedir = get_home_dir()
    download_dir = f'{homedir}/Downloads'
    idx = 0
    old_content = None

    start_seconds = time.time()
    last_seconds = start_seconds
    
    while True:
        now_seconds = time.time()
        total_seconds = now_seconds - start_seconds
        
        current_file = f'{download_dir}/screencap{idx}.png'
        cmd = f'adb shell screencap -p > "{current_file}"'
        if verbose:
            print(f'cmd = {cmd}')
        os.system(cmd)
        idx = (idx + 1) % 2
        
        # read content from current file in binary mode
        with open(current_file, 'rb') as f:
            current_content = f.read()

        if old_content:
            if old_content == current_content:
                print(f"screen is still for {check_interval} seconds, total_seconds={total_seconds}")
                if until == 'still':               
                    return True
            else:
                print(f"screen was moving in last {check_interval} seconds, total_seconds={total_seconds}")
                if until == 'moving':
                    return True
        else:
            print(f"first time to check screen")
        old_content = current_content

        if now_seconds - last_seconds > timeout:
            return False
        
        time.sleep(check_interval)
    


def main():
    import tpsup.androidtools
    tpsup.androidtools.check_android_env()

    if adb_path := which('adb'):
        print(f"adb_path = {adb_path}")
    else:
        raise Exception("adb not found. run adroidenv")

    pkgs = adb_find_pkg('photos')
    print(f"pkgs = {pkgs}")
    print("")

    pkg_path = adb_get_pkg_path(pkgs[0])
    print(f"pkg_path = {pkg_path}")

    adb_pull_pkg('photos')

if __name__ == "__main__":
    main()
