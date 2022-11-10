#!/usr/bin/env python3

user_opt = {
    'verbose' : 1,
    'dryrun' : 1,
    'dir': '/home/myname',
}

def f1 (dir:str, **opt):
    if opt.get('verbose', 0):
        print(f'dir={dir}')
    if opt.get('dryrun', 0):
        print(f'do my work in dir')

# f1(user_opt['dir'], **user_opt) # this will trigger the multiple-values error
f1(**{**user_opt, 'dir':'/home/myname'})



