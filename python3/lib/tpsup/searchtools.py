import os
import sys
from typing import List, Any, Callable, Union


def binary_search_match(arr: List[Any], x: Any,
                        compare: Union[Callable[[Any, Any], int], str],
                        low=None, high=None,
                        verbose=False,
                        InBetween=None,
                        OutBound=None) -> int:
    """
    Searches for the element x in the sorted array arr using binary search algorithm.
    Returns the index of the element if found, else returns -1.
    compare() function:
        target is before, return -1
        target matched,   return 0
        target is after,  return 1
    """
    if isinstance(compare, str):
        if compare == 'cmp' or compare == 'string':
            def compare(a, b):
                if a < b:
                    return -1
                elif a > b:
                    return 1
                else:
                    return 0
        elif compare == '<=>' or compare == 'numeric':
            def compare(a, b): return a - b
            # compare = lambda a, b: a - b
        else:
            raise Exception(
                f'unknown compare method {compare}. only support str, int or a function')
    elif not callable(compare):
        raise Exception(
            f'unknown compare method {compare}. only support str, int or a function')

    if low is None:
        low0 = 0
    elif low < 0:
        raise Exception(f'low={low} must be >= 0')
    else:
        low0 = low

    if high is None:
        high0 = len(arr) - 1
    elif high >= len(arr):
        raise Exception(f'high={high} must be < {len(arr)}')
    else:
        high0 = high

    low = low0
    high = high0

    while low <= high:
        mid = (low + high) // 2
        cmp_result = compare(arr[mid], x)
        if cmp_result == 0:
            return mid
        elif cmp_result < 0:
            low = mid + 1
        else:
            high = mid - 1

    # at this point, low > high

    if low > high0:
        if verbose:
            print(
                f"target {x} is after the last element {arr[high0]}", file=sys.stderr)
        if OutBound is not None:
            if OutBound == 'UseClosest':
                return high0
            elif OutBound == 'Error':
                raise Exception(
                    f"target {x} is after the last element {arr[high0]}")
            else:
                raise Exception(
                    f"'OutBound' must be 'UseClosest' or 'Error'. Yours is '{OutBound}'")
        else:
            return -1
    elif high < low0:
        if verbose:
            print(
                f"target {x} is before the first element {arr[low0]}", file=sys.stderr)
        if OutBound is not None:
            if OutBound == 'UseClosest':
                return low0
            elif OutBound == 'Error':
                raise Exception(
                    f"target {x} is before the first element {arr[low0]}")
            else:
                raise Exception(
                    f"'OutBound' must be 'UseClosest' or 'Error'. Yours is '{OutBound}'")
        else:
            return -1
    else:
        # target is in between 2 elements.
        # remember: at this point, low > high
        if verbose:
            print(
                f"target {x} is between {arr[high]} and {arr[low]}", file=sys.stderr)
        if InBetween is not None:
            if InBetween == 'low':
                return high  # remember: at this point, low > high
            elif InBetween == 'high':
                return low
            elif InBetween == 'Error':
                raise Exception(
                    f"target {x} is between {arr[high]} and {arr[low]}")
            else:
                raise Exception(
                    f"'InBetween' must be 'low', 'high' or 'Error'. Yours is '{InBetween}'")
        else:
            return -1


def binary_search_first(arr: List[Any], testfunc: Callable[[Any], int]) -> int:
    """
    Searches for the 1st element x in the sorted array arr using binary search algorithm.
    Returns the index of the element if found, else returns -1.
    compare() function:
        if target matched, return True or equivallent.
        otherwise, return False or equivalent.

    """
    low = 0
    high = len(arr) - 1
    last_match = None
    while low <= high:
        mid = (low + high) // 2
        cmp_result = testfunc(arr[mid])
        if cmp_result:
            last_match = mid
            high = mid - 1
        else:
            low = mid + 1
    return last_match


def main():
    arr = [1, 2, 4, 10, 12]
    arr2 = ['a', 'b', 'c', 'd', 'e']

    from tpsup.filetools import tpglob
    TPSUP = os.environ.get('TPSUP')
    arr3 = tpglob(f'{TPSUP}/python3/lib/tpsup/searchtools_test*.txt')
    from tpsup.greptools import tpgrep

    def grep2(file):
        return tpgrep(file, 'bc', print_output=False)

    def test_codes():
        binary_search_match(arr, 10, 'numeric')  # expect 3
        binary_search_match(arr2, 'd', 'string')  # expect 3

        binary_search_first(arr, lambda a: a > 4)  # expect 3

        binary_search_match(arr, 15, 'numeric')  # expect -1
        binary_search_match(arr, 15, 'numeric', OutBound='UseClosest')  # 4
        binary_search_match(arr, 9, 'numeric', InBetween='low')  # 2

        binary_search_first(arr3, grep2)  # 3

    from tpsup.testtools import test_lines
    test_lines(test_codes, source_globals=globals(), source_locals=locals())


if __name__ == '__main__':
    main()
