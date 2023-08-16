# python grep equivallent

from tpsup.tpfile import TpInput


def grep(file, MatchPattern: str = None,
         MatchPatterns: list = None,
         ExcludePattern: str = None,
         ExcludePatterns: list = None, **opt):
    """
    grep a file, return a list of matched lines
    """
    verbose = opt.get('verbose', 0)
    if verbose:
        print(f"file = {file}")

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
    with TpInput(filename=file, **opt2, **opt) as tf:
        for line in tf:
            lines.append(line)

    return lines


def main():
    import os
    TPSUP = os.environ.get('TPSUP')
    file = f'{TPSUP}/scripts/tptrace_test.log'

    def test_codes():
        grep(file, 'orderid')
        grep(file, ExcludePattern='orderid')

    from tpsup.exectools import test_lines
    test_lines(test_codes, source_globals=globals(), source_locals=locals())


if __name__ == '__main__':
    main()
