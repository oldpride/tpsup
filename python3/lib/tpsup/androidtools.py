# maily using android sdk tools
from pprint import pformat
import tpsup.cmdtools
import tpsup.adbtools
import tpsup.envtools
import tpsup.javatools
from shutil import which
import os
import tpsup.tmptools

# "%ANDROID_HOME%\tools\bin;
# %ANDROID_HOME%\platform-tools;
# %ANDROID_HOME%\build-tools\33.0.0;
# %ANDROID_HOME%\emulator"

sdk_subdirs = [
    # "tools/bin",
    "cmdline-tools/latest/bin",
    "platform-tools",
    "build-tools/35.0.0", # todo: find the latest version
    "emulator"
]


def set_android_env(**opt):
    verbose = opt.get('verbose', 0)

    # check if adb in th PATH. If yes, we don't need to set android env
    which_adb = tpsup.cmdtools.which('adb')
    if which_adb:
        if verbose:
            print(f'adb found in path: {which_adb}. Android env is already set')
        return

    if not (android_home := os.environ.get('ANDROID_HOME', None)):
        raise Exception('ANDROID_HOME not set')
    else:
        print(f'ANDROID_HOME = {android_home}')
    for subdir in sdk_subdirs:
        tpsup.envtools.add_path(f'{android_home}/{subdir}', **opt)


def check_android_env(**opt):
    if not (android_home := os.environ.get('ANDROID_HOME', None)):
        print('ANDROID_HOME not set')
        return False
    for subdir in sdk_subdirs:
        full_path = f'{android_home}/{subdir}'
        if not os.path.exists(f'{full_path}'):
            print(f'{full_path} not found')
            return False
        if not tpsup.envtools.path_contains(f'{full_path}', **opt):
            print(f'{full_path} not in PATH')
            return False
    return True


# get_apk_manifest() vs get_app_manifest()
#    - get_apk_manifest() only works with apk file.
#    - get_app_manifest() works with app name.
#      it needs adb to be connected to the device or emulator, to download the apk file.
def get_apk_manifest(apk_path: str, method:str="apkanalyzer", **opt):
    verbose = opt.get('verbose', 0)
    '''
    get manifest file from apk

    https://stackoverflow.com/questions/3599210
    '''

    if method == "apkanalyzer":
        '''
        $ androidenv # add androidenv to your path
        $ apkanalyzer manifest print Gallery2.apk # print manifest file
        '''

        set_android_env(**opt)
        # check if apkanalyzer is in path
        # apkanalyzer is in $ANDROID_HOME/cmdline-tools/latest/bin
        # it is a bat script on windows, and a bash script on linux
        # shutil.which() is for bash, cannot find it in windows, 
        # therefore, we use tpsup.cmdtools.which()
        apkanalyzer = tpsup.cmdtools.which('apkanalyzer')
        if not apkanalyzer:
            raise Exception(
                'still cannot find apkanalyzer after setting android env')

        # apkanalyzer works with java 1.8, not java 11
        # tpsup.javatools.set_java_env("1.8")
        # new version of apkanalyzer works with java 17+
        tpsup.javatools.set_java_env("22")
        tpsup.javatools.check_java_env(verbose=1)

        cmd = f'{apkanalyzer.replace('\\', '/')} manifest print "{apk_path}"'
        if verbose:
            print(f'cmd = {cmd}')
        output = tpsup.cmdtools.run_cmd_clean(cmd, is_bash=True, **opt)

    elif method == "aapt":
        '''
        $ aapt dump badging Gallery2.apk
        '''
        aapt = tpsup.cmdtools.which('aapt')
        if not aapt:
            raise Exception('aapt not found in PATH')

        cmd = f'{aapt} dump badging "{apk_path}"'
        if verbose:
            print(f'cmd = {cmd}')
        output = tpsup.cmdtools.run_cmd_clean(cmd, **opt)

    return output


def get_app_manifest(pkg_pattern: str, **opt):
    verbose = opt.get('verbose', 0)
    '''
    get manifest file from app
    '''
    set_android_env(**opt)
    # find package name
    lines = tpsup.adbtools.adb_find_pkg(pkg_pattern, **opt)
    if len(lines) == 0:
        raise Exception(f'no package found for {pkg_pattern}')
    elif len(lines) > 1:
        raise Exception(f'multiple packages found for {pkg_pattern}: {lines}')
    else:
        pkg = lines[0].split(':')[1]

    print(f'pkg = {pkg}')

    # get package path
    device_path = tpsup.adbtools.adb_get_pkg_path(pkg, **opt)
    if not device_path:
        raise Exception(f'no package path found for {pkg}')

    print(f'pkg path on devie = {device_path}')
    print("")

    # pull the file using adb
    local_path = tpsup.adbtools.adb_pull(device_path, **opt)
    print(f'pulled apk file from device to local path = {local_path}')
    print("")

    # check if path is a file
    if not os.path.isfile(local_path):
        raise Exception(f'{local_path} is not a file')

    # get manifest file
    manifest = get_apk_manifest(local_path, **opt)

    return manifest


def main():
    # start emulator first
    # $ ptappium start_emulator

    app='photos'
    for method in ["apkanalyzer", "aapt"]:
        print()
        print("----------------------------------------------")
        print(f'method = {method}')
        print(get_app_manifest(app, method=method))
        



if __name__ == '__main__':
    main()
