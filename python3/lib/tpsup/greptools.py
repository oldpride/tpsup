# python grep equivallent

from glob import glob
import os
import re
import sys
from typing import Union
from tpsup.filetools import TpInput, tpglob
from tpsup.logtools import log_FileFuncLine
from tpsup.searchtools import binary_search_first


def grep(files: Union[list, str], MatchPattern: str = None,
         MatchPatterns: list = None,
         ExcludePattern: str = None,
         ExcludePatterns: list = None,
         FileNameOnly: bool = False,
         Recursive: bool = False,
         FindFirstFile=False,
         **opt):
    """
    grep a file, return a list of matched lines
    """

    verbose = opt.get('verbose', 0)
    print_output = opt.get('print_output', False)

    if isinstance(files, str):
        # split string by space or newline
        files2 = re.split('\s+', files, re.MULTILINE)
    else:
        files2 = files

    files3 = tpglob(files, **opt)

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

    lines2 = []
    seen_file = {}

    print_filename = len(files2) > 1 or Recursive
    exclude_dirs = set(['.git', '.idea', '__pycache__', '.snapshot'])

    # define a function inside a function to save from passing parameters
    def grep_1_file(f: str):
        lines = []
        with TpInput(filename=f, **opt) as tf:
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
                        lines.append(f)
                        if opt.get('print_output', False):
                            print(f)
                        break

                    if print_filename:
                        lines.append(f'{f}:{line}')
                        if print_output:
                            print(f'{f}:{line}', end='')
                    else:
                        lines.append(line)
                        if print_output:
                            print(line, end='')
            except UnicodeDecodeError as e:
                # UnicodeDecodeError: 'utf-8' codec can't decode byte 0x9b in position 147:
                #     invalid start byte
                print(
                    f'grep {f} failed with decode error. skipped.', file=sys.stderr)
                if verbose:
                    print(e, file=sys.stderr)

        return lines

    if FindFirstFile:
        # use binary search to find the first file has the match
        def grep2(f):
            return grep_1_file(f)
        index = binary_search_first(files3, grep2)
        return files3[index] if index >= 0 else None
    else:
        for file in files3:
            if file in seen_file:
                if verbose:
                    log_FileFuncLine(
                        f'{file} already seen, skip', file=sys.stderr)
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
                            matches = grep_1_file(full_path)
                            lines2.extend(matches)
                else:
                    if verbose:
                        print(f'{file} is a directory, skip', file=sys.stderr)
                continue

            if verbose:
                print(f'grep {file}', file=sys.stderr)

            match = grep_1_file(file)
            lines2.extend(match)

        return lines2


def main():
    import os
    TPSUP = os.environ.get('TPSUP')
    files1 = f'{TPSUP}/python3/scripts/ptgrep_test*'
    files2 = f'{TPSUP}/python3/lib/tpsup/searchtools_test*'

    def test_codes():
        grep(files1, 'mypattern')
        grep(files1, ExcludePattern='abc|def')
        grep(files1, 'mypattern', FileNameOnly=True)
        grep(files2, 'bc', FindFirstFile=True)
        grep(files2, 'bc', FindFirstFile=True, sort='time')

    from tpsup.exectools import test_lines
    test_lines(test_codes, source_globals=globals(), source_locals=locals())


if __name__ == '__main__':
    main()
