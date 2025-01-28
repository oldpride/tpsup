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
        https://stackoverflow.com/questions/3599210
        $ aapt dump badging photos.apk
        '''
        aapt = tpsup.cmdtools.which(method).replace('\\', '/')
        if not aapt:
            raise Exception('aapt not found in PATH')

        cmd = f'{aapt} dump xmltree "{apk_path}" AndroidManifest.xml'
        if verbose:
            print(f'cmd = {cmd}')
        output = tpsup.cmdtools.run_cmd_clean(cmd, **opt)
    elif method == "aapt2":
        '''
        https://developer.android.com/tools/aapt2
        '''
        exe = tpsup.cmdtools.which(method).replace('\\', '/')
        if not exe:
            raise Exception(f'{method} not found in PATH')
        if verbose:
            print(f'{method} = {exe}')

        cmd = f'{exe} dump xmltree "{apk_path}" --file AndroidManifest.xml'
        if verbose:
            print(f'cmd = {cmd}')
        output = tpsup.cmdtools.run_cmd_clean(cmd, **opt)
    elif method == "apktool":
        '''
        https://stackoverflow.com/questions/3599210
        apktool.bat decode -f -o downloads \
            C:/Users/tian/AppData/Local/Temp/daily/20250127/com.google.android.apps.photos.apk
        '''
        exe = tpsup.cmdtools.which(method).replace('\\', '/')
        if not exe:
            raise Exception(f'{method} not found in PATH')
        if verbose:
            print(f'{method} = {exe}')

        # normally we download apk file to a daily directory, but
        # apktool will clean up its output directory, so we need 
        # to direct apktool to a different directory so that the
        # apk file is not deleted.
        tmpdir = tpsup.tmptools.get_dailydir().replace('\\', '/')
        tmpdir = f'{tmpdir}/apktool'
        cmd = f'{exe} decode -f -o {tmpdir} "{apk_path}"'
        if verbose:
            print(f'cmd = {cmd}')

        output2 = tpsup.cmdtools.run_cmd_clean(cmd, **opt)  

        if verbose:
            print(f'output2 = {output2}')

        mainfest_file = f'{tmpdir}/AndroidManifest.xml'
        if not os.path.exists(mainfest_file):
            raise Exception(f'cannot find {mainfest_file}')
        with open(mainfest_file, 'r') as f:
            output = f.read()
    else:
        raise Exception(f'unsupported method={method}')      
    

    return output


def get_app_manifest(pkg_pattern: str, **opt):
    verbose = opt.get('verbose', 0)
    '''
    get manifest file from app
    '''
    set_android_env(**opt)
    
    # pull the file using adb
    local_path = tpsup.adbtools.adb_pull_pkg(pkg_pattern, **opt)
    print(f'apk file local path = {local_path}')
    print("")

    # get manifest file
    manifest = get_apk_manifest(local_path, **opt)

    return manifest


def main():
    # start emulator first
    # $ ptappium start_emulator

    app='photos'
    for method in [
            "apkanalyzer", 
            "aapt",
            'aapt2',
            "apktool",
        ]:
        print()
        print("----------------------------------------------")
        print(f'method = {method}')
        print(get_app_manifest(app, method=method))
        



if __name__ == '__main__':
    main()
