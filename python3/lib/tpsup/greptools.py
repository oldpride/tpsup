# python grep equivallent

from glob import glob
import os
import re
import sys
from typing import Union
from tpsup.tpfile import TpInput


def grep(files: Union[list, str], MatchPattern: str = None,
         MatchPatterns: list = None,
         ExcludePattern: str = None,
         ExcludePatterns: list = None,
         FileNameOnly: bool = False,
         **opt):
    """
    grep a file, return a list of matched lines
    """
    verbose = opt.get('verbose', 0)
    files2 = []
    if isinstance(files, str):
        # split string by space or newline
        for f in re.split('\s+', files, re.MULTILINE):
            files2.extend(glob(f))
    else:
        for f in files:
            files2.extend(glob(f))

    opt2 = {}
    if MatchPatterns:
        opt2['MatchPatterns'] = MatchPatterns
    elif MatchPattern:
        opt2['MatchPatterns'] = [MatchPattern]

    if ExcludePatterns:
        opt2['ExcludePatterns'] = ExcludePatterns
    elif ExcludePattern:
        opt2['ExcludePatterns'] = [ExcludePattern]

    lines = []
    seen_file = {}

    print_filename = len(files2) > 1
    for file in files2:
        if seen_file.get('file', False):
            continue
        else:
            seen_file[file] = True

        # skip directories
        if os.path.isdir(file):
            print(f'{file} is a directory, skip', file=sys.stderr)
            continue

        if verbose:
            print(f'grep {file}', file=sys.stderr)

        with TpInput(filename=file, **opt2, **opt) as tf:
            # Regex is built inside TpInput

            try:
                for line in tf:  # this line may raise exception for binary file. so use try/except
                    if FileNameOnly:
                        lines.append(file)
                        if opt.get('print', False):
                            print(file)
                        break

                    if print_filename:
                        lines.append(f'{file}:{line}')
                        if opt.get('print', False):
                            print(f'{file}:{line}', end='')
                    else:
                        lines.append(line)
                        if opt.get('print', False):
                            print(line, end='')
            except UnicodeDecodeError as e:
                # UnicodeDecodeError: 'utf-8' codec can't decode byte 0x9b in position 147:
                #     invalid start byte
                print(
                    f'grep {file} failed with decode error. skipped.', file=sys.stderr)
                if verbose:
                    print(e, file=sys.stderr)
                continue

    return lines


def grepl(files: Union[list, str], MatchPatterns: list, **opt):
    """
    extend unix "grep -l" to support multiple patterns
    """
    verbose = opt.get('verbose', 0)
    files2 = []
    if isinstance(files, str):
        # split string by space or newline
        for f in re.split('\s+', files, re.MULTILINE):
            files2.extend(glob(f))
    else:
        for f in files:
            files2.extend(glob(f))

    files3 = []
    if len((MatchPatterns)) == 0:
        raise RuntimeError('MatchPatterns is empty')

    CompiledPatterns = {}
    for p in MatchPatterns:
        CompiledPatterns[p] = re.compile(p)

    seen_file = {}

    for file in files2:
        if seen_file.get('file', False):
            continue
        else:
            seen_file[file] = True

        # skip directories
        if os.path.isdir(file):
            print(f'{file} is a directory, skip', file=sys.stderr)
            continue

        if verbose:
            print(f'grep {file}', file=sys.stderr)

        c2 = CompiledPatterns.copy()  # copy to avoid changing the original

        with TpInput(filename=file, **opt) as tf:
            # Regex is built inside TpInput

            try:
                for line in tf:
                    (keys, values) = zip(*CompiledPatterns.items())
                    for i in range(len(keys)):
                        if values[i].search(line):
                            c2.pop(keys[i])
                    # checkif c2 is empty
                    if len(c2) == 0:
                        files3.append(file)
                        if opt.get('print', False):
                            print(file)
                        break
            except UnicodeDecodeError as e:
                # UnicodeDecodeError: 'utf-8' codec can't decode byte 0x9b in position 147:
                #     invalid start byte
                print(
                    f'grep {file} failed with decode error. skipped.', file=sys.stderr)
                if verbose:
                    print(e, file=sys.stderr)
                continue

    return files3


def main():
    import os
    TPSUP = os.environ.get('TPSUP')
    files = f'{TPSUP}/python3/scripts/grep_test*'

    def test_codes():
        grep(files, 'mypattern')
        grep(files, ExcludePattern='abc|def')
        grep(files, 'mypattern', FileNameOnly=True)
        grepl(files, ['mypattern', 'abc1'])

    from tpsup.exectools import test_lines
    test_lines(test_codes, source_globals=globals(), source_locals=locals())


if __name__ == '__main__':
    main()
