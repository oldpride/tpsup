# python grep equivallent

from glob import glob
import os
import re
import sys
from typing import Union
from tpsup.filetools import TpInput, tpglob, tpfind
from tpsup.logbasic import log_FileFuncLine
from tpsup.searchtools import binary_search_first


def tpgrep(files: Union[list, str],
           MatchPattern: str = None,
           MatchPatterns: list = None,
           ExcludePattern: str = None,
           ExcludePatterns: list = None,
           FileNameOnly: bool = False,
           Recursive: bool = False,
           MaxDepth: int = None,
           FindFirstFile: bool = False,
           print_output: bool = False,
           CaseInsensitive: bool = False,
           **opt):
    """
    grep a file, return a list of matched lines
    """

    # verbose will be passed to downstream functions, therefore, it stays in **opt
    verbose = opt.get('verbose', 0)

    if not Recursive:
        MaxDepth = 0

    found = tpfind(files,
                   MaxDepth=MaxDepth,
                   MatchExps=['r["type"] != "dir"'],
                   no_print=True,
                   **opt)

    files2 = [r['path'] for r in found["hashes"]]

    if '-' in files:
        # tpfind will throw away '-' because it is not a file. we need to add it back
        files2.append('-')

    print_filename = len(files2) > 1

    if verbose:
        print(f'files2={files2}', file=sys.stderr)

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
    # print(f'MatchPatterns2={MatchPatterns2}', file=sys.stderr)
    # print(f'ExcludePatterns2={ExcludePatterns2}', file=sys.stderr)  # toremove

    MatchCompiled = []
    if MatchPatterns2:
        for p in MatchPatterns2:
            if CaseInsensitive:
                MatchCompiled.append(re.compile(p, re.IGNORECASE))
            else:
                MatchCompiled.append(re.compile(p))
    ExcludeCompiled = []
    if ExcludePatterns2:
        for p in ExcludePatterns2:
            if CaseInsensitive:
                ExcludeCompiled.append(re.compile(p, re.IGNORECASE))
            else:
                ExcludeCompiled.append(re.compile(p))

    lines2 = []

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
                                # print(f'exclude {f}:{line}',
                                #       file=sys.stderr)  # toremove
                                to_exclude = True
                                break
                    if to_exclude:
                        continue

                    if FileNameOnly:
                        lines.append(f)
                        if print_output:
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
        index = binary_search_first(files2, grep2)
        return files2[index] if index >= 0 else None
    else:
        seen_file = {}
        for file in files2:
            if file in seen_file:
                if verbose:
                    log_FileFuncLine(
                        f'file={file} already seen, skip', file=sys.stderr)
                continue
            else:
                seen_file[file] = True

            match = grep_1_file(file)
            lines2.extend(match)

        return lines2


def main():
    import os
    TPSUP = os.environ.get('TPSUP')
    files1 = f'{TPSUP}/python3/scripts/ptgrep_test*'
    files2 = f'{TPSUP}/python3/lib/tpsup/searchtools_test*'

    def test_codes():
        tpgrep(files1, 'Mypattern', CaseInsensitive=True)
        tpgrep(files1, ExcludePattern='abc|def')
        tpgrep(files1, 'mypattern', FileNameOnly=True)
        tpgrep(files2, 'bc', FindFirstFile=True)
        tpgrep(files2, 'bc', FindFirstFile=True, sort_name='mtime')

    from tpsup.testtools import test_lines
    test_lines(test_codes, source_globals=globals(), source_locals=locals())


if __name__ == '__main__':
    main()
