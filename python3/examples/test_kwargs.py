#!/usr/bin/env python3


def change_kwargs(**kwargs):
    print('got ', kwargs)
    kwargs['new'] = 'new item'
    print('set to ', kwargs)


def main():
    kwargs = {'a': 1, 'b': 2}

    print('before, outer = ', kwargs)
    change_kwargs(**kwargs)
    print('after, outer =', kwargs)


if __name__ == '__main__':
    main()