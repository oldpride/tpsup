# python grep equivallent

from glob import glob
import os
import re
import sys
from typing import Union
from tpsup.tpfile import TpInput, tpglob
from tpsup.tplog import log_FileFuncLine


def grep(files: Union[list, str], MatchPattern: str = None,
         MatchPatterns: list = None,
         ExcludePattern: str = None,
         ExcludePatterns: list = None,
         FileNameOnly: bool = False,
         Recursive: bool = False,
         **opt):
    """
    grep a file, return a list of matched lines
    """

    verbose = opt.get('verbose', 0)

    if isinstance(files, str):
        # split string by space or newline
        files2 = re.split('\s+', files, re.MULTILINE)
    else:
        files2 = files

    files3 = tpglob(files)

    if verbose:
        print(f'files3={files3}', file=sys.stderr)

    if MatchPatterns:
        MatchPatterns2 = MatchPatterns
    elif MatchPattern:
        MatchPatterns2 = [MatchPattern]
    else:
        MatchPatterns2 = []

    if ExcludePatterns:
        ExcludePatterns2 = ExcludePatterns
    elif ExcludePattern:
        ExcludePatterns2 = [ExcludePattern]
    else:
        ExcludePatterns2 = []

    MatchCompiled = []
    if MatchPatterns2:
        for p in MatchPatterns2:
            if opt.get('CaseInsensitive', False):
                MatchCompiled.append(re.compile(p, re.IGNORECASE))
            else:
                MatchCompiled.append(re.compile(p))
    ExcludeCompiled = []
    if ExcludePatterns2:
        for p in ExcludePatterns2:
            if opt.get('CaseInsensitive', False):
                ExcludeCompiled.append(re.compile(p, re.IGNORECASE))
            else:
                ExcludeCompiled.append(re.compile(p))

    lines = []
    seen_file = {}

    print_filename = len(files2) > 1 or Recursive
    exclude_dirs = set(['.git', '.idea', '__pycache__', '.snapshot'])
    for file in files3:
        if file in seen_file:
            if verbose:
                log_FileFuncLine(f'{file} already seen, skip', file=sys.stderr)
            continue
        else:
            seen_file[file] = True

        # skip directories
        if os.path.isdir(file):
            if Recursive:
                if file in exclude_dirs:
                    if verbose:
                        log_FileFuncLine(
                            f'{file} is in exclude_dirs, skip', file=sys.stderr)
                    continue

                for root, dirs, fnames in os.walk(file, topdown=True):
                    # https://stackoverflow.com/questions/19859840/excluding-directories-in-os-walk
                    # key point: use [:] to modify dirs in place
                    dirs[:] = [d for d in dirs if d not in exclude_dirs]
                    for f in fnames:
                        full_path = os.path.join(root, f)
                        if verbose:
                            print(f'grep {full_path}', file=sys.stderr)
                        matches = grep_1_file(full_path,
                                              MatchCompiled=MatchCompiled,
                                              ExcludeCompiled=ExcludeCompiled,
                                              FileNameOnly=FileNameOnly,
                                              print_filename=print_filename,
                                              **opt)
                        lines.extend(matches)
            else:
                if verbose:
                    print(f'{file} is a directory, skip', file=sys.stderr)
            continue

        if verbose:
            print(f'grep {file}', file=sys.stderr)

        match = grep_1_file(file,
                            MatchCompiled=MatchCompiled,
                            ExcludeCompiled=ExcludeCompiled,
                            FileNameOnly=FileNameOnly,
                            print_filename=print_filename,
                            **opt)
        lines.extend(match)

    return lines


def grep_1_file(file: str,
                MatchCompiled: list = None,
                ExcludeCompiled: list = None,
                FileNameOnly: bool = False,
                print_filename: bool = False,
                **opt):
    verbose = opt.get('verbose', 0)

    lines = []
    with TpInput(filename=file, **opt) as tf:
        # Regex is built inside TpInput

        try:
            for line in tf:  # this line may raise exception for binary file. so use try/except
                if verbose > 2:
                    print(f'line={line}', file=sys.stderr)

                if MatchCompiled:
                    all_matched = True
                    for p in MatchCompiled:
                        if not p.search(line):
                            all_matched = False
                            break
                    if not all_matched:
                        continue

                to_exclude = False
                if ExcludeCompiled:
                    for p in ExcludeCompiled:
                        if p.search(line):
                            to_exclude = True
                            break
                if to_exclude:
                    continue

                if FileNameOnly:
                    lines.append(file)
                    if opt.get('print_output', False):
                        print(file)
                    break

                if print_filename:
                    lines.append(f'{file}:{line}')
                    if opt.get('print_output', False):
                        print(f'{file}:{line}', end='')
                else:
                    lines.append(line)
                    if opt.get('print_output', False):
                        print(line, end='')
        except UnicodeDecodeError as e:
            # UnicodeDecodeError: 'utf-8' codec can't decode byte 0x9b in position 147:
            #     invalid start byte
            print(
                f'grep {file} failed with decode error. skipped.', file=sys.stderr)
            if verbose:
                print(e, file=sys.stderr)

    return lines


def main():
    import os
    TPSUP = os.environ.get('TPSUP')
    files = f'{TPSUP}/python3/scripts/grep_test*'

    def test_codes():
        grep(files, 'mypattern')
        grep(files, ExcludePattern='abc|def')
        grep(files, 'mypattern', FileNameOnly=True)

    from tpsup.exectools import test_lines
    test_lines(test_codes, source_globals=globals(), source_locals=locals())


if __name__ == '__main__':
    main()
