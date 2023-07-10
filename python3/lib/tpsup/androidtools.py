import tpsup.cmdtools


def get_apk_manifest(apk_path: str, **opt):
    verbose = opt.get('verbose', 0)
    '''
    get manifest file from apk

    $ androidenv # add androidenv to your path
    $ apkanalyzer manifest print Gallery2.apk # print manifest file
    '''
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

    return output


def main():
    print(get_apk_manifest('Gallery2.apk'))


if __name__ == '__main__':
    main()
