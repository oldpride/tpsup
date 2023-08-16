# python grep equivallent

import re
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
    if isinstance(files, str):
        # split string by space or newline
        files2 = re.split('\s+', files, re.MULTILINE)
    else:
        files2 = files

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

        with TpInput(filename=file, **opt2, **opt) as tf:
            # Regex is built inside TpInput
            for line in tf:
                if FileNameOnly:
                    lines.append(file)
                    break

                if print_filename:
                    lines.append(f'{file}:{line}')
                else:
                    lines.append(line)

    return lines


def main():
    import os
    TPSUP = os.environ.get('TPSUP')
    file = f'{TPSUP}/scripts/tptrace_test.log'

    def test_codes():
        grep(file, 'orderid')
        grep(file, ExcludePattern='orderid')
        grep(file, 'orderid', FileNameOnly=True)

    from tpsup.exectools import test_lines
    test_lines(test_codes, source_globals=globals(), source_locals=locals())


if __name__ == '__main__':
    main()
