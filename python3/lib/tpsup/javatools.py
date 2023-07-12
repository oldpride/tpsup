# maily using android sdk tools
from pprint import pformat
import re
import tpsup.cmdtools
import tpsup.adbtools
import tpsup.env
from shutil import which
import os
import tpsup.tptmp


def set_java_env(version, **opt):
    my_env = tpsup.env.Env()
    if my_env.isWindows:
        possible_places = [f"{my_env.home_dir}/java", 'C:/Program Files/Java']
    elif my_env.isLinux:
        possible_places = [f"{my_env.home_dir}/java", '/usr/lib/jvm']
    else:
        raise Exception('unsupported OS')

    for j in ['jdk', 'jre']:
        # favor jdk over jre
        patterns = [re.compile(f'{j}[^0-9]*{version}$|[^0-9]*{version}[^0-9]'),
                    re.compile(f'[^0-9]+{version}[^0-9]*{j}|^{version}[^0-9]*{j}')]
        for java_base in possible_places:
            if os.path.exists(java_base):
                subdirs = os.listdir(java_base)
                for subdir in subdirs:
                    for p in patterns:
                        if p.search(subdir):
                            full_path = f'{java_base}/{subdir}/bin'
                            if os.path.exists(full_path):
                                java_home = f'{java_base}/{subdir}'
                                os.environ['JAVA_HOME'] = java_home
                                tpsup.env.add_path(full_path, place='prepend')
                                return java_home
    return None


def check_java_env(**opt):
    verbose = opt.get('verbose', 0)
    if not (JAVA_HOME := os.environ.get('JAVA_HOME', None)):
        print('JAVA_HOME not set')
        return False
    if verbose:
        print(f'JAVA_HOME={JAVA_HOME}')

    if not os.path.exists(JAVA_HOME):
        print(f'JAVA_HOME={JAVA_HOME} dir not found')
        return False

    if not os.path.exists(f'{JAVA_HOME}/bin'):
        print(f'JAVA_HOME={JAVA_HOME}/bin dir not found')
        return False
    if verbose:
        print(f'{JAVA_HOME}/bin is PATH')

    for exe in ['java', 'javac', 'jar']:
        if not (paths := tpsup.cmdtools.which(exe)):
            print(f'{exe} not found in PATH')
            return False
        if verbose:
            print(f'{exe} found in PATH: {pformat(paths)}')

    return True


def main():
    print(f'JAVA_HOME={os.environ.get("JAVA_HOME", None)}')
    print("")
    print(f"set_java_env('1.8')={set_java_env('1.8')}")
    check_java_env(verbose=1)
    print("")
    print(f"set_java_env('11')={set_java_env('11')}")
    check_java_env(verbose=1)
    print("")


if __name__ == '__main__':
    main()
