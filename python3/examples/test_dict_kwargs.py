#!/usr/bin/env python3


def change_kwargs(d1, **kwargs):
    print('got dict in func', d1)
    d1['new_dict'] = 'new dict item'
    print('set dict in func', d1)

    print('')

    print('got kwargs in func', kwargs)
    kwargs['new_kwarg'] = 'new kwarg item'
    print('set kwargs in func', kwargs)

    print('')


def main():
    """ dict is passed by reference, **kwargs is passed by value"""

    print("dict is passed by reference, **kwargs is passed by value")
    d = {'a': 1, 'b': 2}
    kwargs = {'a': 1, 'b': 2}

    print('before, dict in main = ', d)
    print('before, kwarg in main = ', kwargs)

    change_kwargs(d, **kwargs)

    print('after, dict in main =', d)
    print('after, kwarg in main =', kwargs)


if __name__ == '__main__':
    main()