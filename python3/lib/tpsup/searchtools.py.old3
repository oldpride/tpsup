import os
from typing import List, Any, Callable


def binary_search_match(arr: List[Any], x: Any, compare: Callable[[Any, Any], int]) -> int:
    """
    Searches for the element x in the sorted array arr using binary search algorithm.
    Returns the index of the element if found, else returns -1.
    compare() function:
        target is before, return -1
        target matched,   return 0
        target is after,  return 1
    """
    low = 0
    high = len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        cmp_result = compare(arr[mid], x)
        if cmp_result == 0:
            return mid
        elif cmp_result < 0:
            low = mid + 1
        else:
            high = mid - 1
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
    arr = [2, 3, 4, 10, 40]
    x = 10
    result = binary_search_match(arr, x, lambda a, b: a - b)
    print(f"arr={arr}, target={x}, result={result}, expect=3")

    result = binary_search_first(arr, lambda a: a > 4)
    print(f"arr={arr}, target={x}, result={result}, expect=3")

    from tpsup.filetools import tpglob
    TPSUP = os.environ.get('TPSUP')
    arr = tpglob(f'{TPSUP}/python3/lib/tpsup/searchtools_test*.txt')
    x = "bc"

    from tpsup.greptools import grep

    def grep2(file):
        return grep(file, x, print_output=False)

    result = binary_search_first(arr, grep2)
    result_file = arr[result] if result >= 0 else None
    print(f"arr={arr}, target={x}, result={result}, expect=3")
    print(f"result_file = {result_file}")


if __name__ == '__main__':
    main()
