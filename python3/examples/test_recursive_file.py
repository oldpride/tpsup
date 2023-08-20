#!/usr/bin/env python

import os

for path in [
    os.environ['TPSUP'].replace("\\", "/") + '/python3/scripts',
    os.environ['TPSUP'].replace("\\", "/") + '/python3/scripts/tpgrep',
]:
    print(f'path={path}')

    exclude_dirs = set(['.git', '.idea', '__pycache__', '.snapshot'])

    for root, dirs, fnames in os.walk(path, topdown=True):
        # https://stackoverflow.com/questions/19859840/excluding-directories-in-os-walk
        # key point: use [:] to modify dirs in place
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        print(f'root={root}')
        print(f'dirs={dirs}')
        print(f'fnames={fnames}')
        print('')
