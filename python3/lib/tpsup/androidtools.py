# maily using android sdk tools
import tpsup.cmdtools
import tpsup.adbtools
from shutil import which
import os


def set_android_env(**opt):
    if not (android_home := os.environ.get('ANDROID_HOME', None)):
        raise Exception('ANDROID_HOME not set')


def get_apk_manifest(apk_path: str, **opt):
    verbose = opt.get('verbose', 0)
    '''
    get manifest file from apk

    $ androidenv # add androidenv to your path
    $ apkanalyzer manifest print Gallery2.apk # print manifest file
    '''
    # check if apkanalyzer is in path
    if not which('apkanalyzer'):
        print('apkanalyzer not found in path. try ANDROID_HOME')
        # check if ANDROID_HOME is set
        if not (android_home := os.environ.get('ANDROID_HOME', None)):
            raise Exception('ANDROID_HOME not set')

    cmd = f'apkanalyzer manifest print {apk_path}'
    if verbose:
        print(f'cmd = {cmd}')
    output = tpsup.cmdtools.run_cmd_clean(cmd, **opt)

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

    # get package path
    path = tpsup.adbtools.adb_get_pkg_path(pkg, **opt)
    if not path:
        raise Exception(f'no package path found for {pkg}')

    # pull apk
    download_path = tpsup.adbtools.adb_pull(path, **opt)

    # get manifest file
    manifest = get_apk_manifest(download_path, **opt)

    return manifest


def main():
    # print(get_apk_manifest('Gallery2.apk'))

    # start emulator first
    # $ svenv
    # $ appium_emulator.bash start
    print(f'get_app_manifest("gallery") = {get_app_manifest("gallery")}')


if __name__ == '__main__':
    main()
