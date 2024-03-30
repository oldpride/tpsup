#!/usr/bin/env python
import tpsup.envtools
import tpsup.csvtools
import tpsup.htmltools

import tpsup.seleniumtools
import tpsup.pstools
import tpsup.swaggertools

# functions mentioned here are called by tpsup.batch, therefore,
# if the function is defined elsewhere, we need to import module and mention the module.


def swagger_test_validator(a: list, cfg: dict, **opt):
    if 'hello' in a[0]:
        print(f'validating {a[0]}: matched hello')
        return 1
    else:
        print(f'validating {a[0]}: not matched hello')
        return 0


def is_Cusip(a):
    if len(a) == 9:
        print(f'validating {a}: matched Cusip')
        return 1
    else:
        print(f'validating {a}: not matched Cusip')
        return 0


# add this function to tpsup.swaggertools namespace because it is will be called
# by tpsup.swaggertools.swagger() function.
tpsup.swaggertools.is_Cusip = is_Cusip

our_cfg = {
    'minimal_args': 2,

    'module': 'tpsup.swaggertools',

    'extra_args': {
        'nojson': {'switches': ['-nojson', '--nojson'],
                   'default': False,
                   'action': 'store_true',
                   'help': 'disable reformat output using json formatter'
                   },
    },

    'cfg': {
        'mybase1': {
            'base_urls': ['https://myhost1.abc.com:9100'],
            'entry': 'swagger-tian',
            'op': {
                'myop1_1': {
                    'num_args': 1,
                    'sub_url': 'app1/api/run_myop1_1',
                    'json': 1,
                    'method': 'POST',
                    'post_data': '{{A0}}',
                    # eval a funtion defined in another module, just prefix it.
                    'validator': "re.search('hello', '{{A0}}')",
                    'comment': 'run myop1_1',
                    'test_str': ['{"hello world"}'],  # two tests here
                },
                'myop1_2': {
                    'num_args': 1,
                    'sub_url': 'app1/api/run_myop1_2',
                    'json': 1,
                    'method': 'POST',
                    'post_data': '["hard coded"]',
                    # eval a function defined in this module.
                    # because eval() is called from tpsup.swaggertools.swagger(), therefore,
                    # it is in tpsup.swaggertools namespace.
                    # is_Cusip() is defined in this module, therefore, it is in
                    # tpsup.batch namespace.
                    # So we need to prefix is_Cusip() with tpsup.batch, so that eval() can find it.
                    # 'validator': "tpsup.batch.is_Cusip('{{A0}}')",
                    # after we did tpsup.swaggertools.is_Cusip = is_Cusip, we can use
                    'validator': "is_Cusip('{{A0}}')",
                    'comment': 'run myop1',
                    'test_str': ['123456789', '12345'],  # two tests here
                },
                'myop1_3': {
                    'num_args': 1,
                    'sub_url': 'app1/api/run_myop1_3/{{A0}}',
                    'json': 1,
                    'validator': swagger_test_validator,
                    'comment': 'run myop1_3',
                    'test_str': ['hello', 'world'],  # two tests here
                },
            },
        },

        'mybase2': {
            'base_urls': ['https://myhost1.abc.com:9102', 'https://myhost2.abc.com:9102'],
            # functions mentioned here are called by tpsup.batch, therefore,
            # if the function is defined elsewhere, we need to import module and mention the module.
            'entry': tpsup.swaggertools.get_entry_by_method_suburl,
            'op': {
                'myop2_1': {
                    'num_args': 2,
                    'sub_url': 'app2/api/run_myop2/{{A0}}/{{A1}}',
                    'Accept': 'text/xml',
                    'comment': 'run myop2_1',
                    'test_str': ['hello world', '''"don't" answer'''],
                },
            },
        },
    },
}
