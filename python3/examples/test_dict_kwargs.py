#!/usr/bin/env python3


def change_kwargs(_d1, _d2, **_kwargs):
    print('got _d1 in func', _d1)
    _d1['new_dict'] = 'new dict item'
    print('set _d1 in func', _d1)

    print('')

    _d2_copy = dict(_d2)
    print('got _d2_copy in func', _d2_copy)
    _d2_copy['new_dict'] = 'new dict item'
    print('set _d2_copy in func', _d2_copy)

    print('')

    print('got _kwargs in func', _kwargs)
    _kwargs['new_kwarg'] = 'new kwarg item'
    print('set _kwargs in func', _kwargs)

    print('')


def main():
    """ dict is passed by reference, **kwargs is passed by value"""

    print("dict is passed by reference, **kwargs is passed by value")
    d1 = {'a': 1, 'b': 2}
    d2 = {'a': 1, 'b': 2}
    kwargs = {'a': 1, 'b': 2}

    print('before, dict d1 in main = ', d1)
    print('before, dict d2 in main = ', d2)
    print('before, kwarg in main = ', kwargs)

    change_kwargs(d1, d2, **kwargs)

    print('after, dict d1 in main =', d1)
    print('after, dict d2 in main =', d2)
    print('after, kwarg in main =', kwargs)


if __name__ == '__main__':
    main()