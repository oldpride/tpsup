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
def get_apk_manifest(apk_path: str, **opt):
    verbose = opt.get('verbose', 0)
    '''
    get manifest file from apk

    $ androidenv # add androidenv to your path
    $ apkanalyzer manifest print Gallery2.apk # print manifest file
    '''
    # check if apkanalyzer is in path
    # apkanalyzer is in $ANDROID_HOME/cmdline-tools/latest/bin
    # it is a bat script on windows, and a bash script on linux
    # shutil.which() cannot find it (bash) in windows, therefore, we use tpsup.cmdtools.which()
    which_result = tpsup.cmdtools.which('apkanalyzer')
    if which_result:
        print(f'apkanalyzer found in path: {which_result}')
    else:
        print('apkanalyzer not found in path. trying to set android env ...')
        # check if ANDROID_HOME is set
        set_android_env(**opt)
        if not check_android_env(**opt):
            raise Exception('android env is not set correctly')
        else:
            print('android env is set correctly')

        print('PATH =' + pformat(os.environ['PATH'].split(os.pathsep)))

        # check again
        which_result = tpsup.cmdtools.which('apkanalyzer')
        if which_result:
            print(f'apkanalyzer found in path: {which_result} after setting android env')
        else:
            raise Exception(
                'still cannot find apkanalyzer after setting android env')

    # apkanalyzer works with java 1.8, not java 11
    # tpsup.javatools.set_java_env("1.8")
    # new version of apkanalyzer works with java 17+
    tpsup.javatools.set_java_env("22")
    tpsup.javatools.check_java_env(verbose=1)

    cmd = f'{which_result.replace('\\', '/')} manifest print "{apk_path}"'
    if verbose:
        print(f'cmd = {cmd}')
    output = tpsup.cmdtools.run_cmd_clean(cmd, is_bash=True, **opt)

    return output


def get_app_manifest(pkg_pattern: str, **opt):
    verbose = opt.get('verbose', 0)
    '''
    get manifest file from app
    '''

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
    dailydir = tpsup.tmptools.get_dailydir()

    # if os.path.exists(f'{dailydir}/Gallery2.apk'):
    #     print(f"manifest of {dailydir}/Gallery2.apk")
    #     print(get_apk_manifest(f'{dailydir}/Gallery2.apk'))

    # start emulator first
    # $ svenv
    # $ appium_emulator.bash start
    print(f'get_app_manifest("gallery") = {get_app_manifest("gallery")}')


if __name__ == '__main__':
    main()
