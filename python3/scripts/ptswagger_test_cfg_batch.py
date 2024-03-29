#!/usr/bin/env python
import tpsup.envtools
import tpsup.csvtools
import tpsup.htmltools

import tpsup.seleniumtools
import tpsup.pstools
import tpsup.swaggertools


our_cfg = {
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
                    # json requires double string for its strings. therefore, we use single
                    # quote below.
                    'validator': "re.search('{{A0}}', 'hello')",
                    'comment': 'run myop1_1',
                    'test_str': ["abc",  '{"hello world"}'],  # two tests here
                },
                'myop1_2': {
                    'sub_url': 'app1/api/run_myop1_2',
                    'json': 1,
                    'method': 'POST',
                    'post_data': '["hard coded"]',
                    'comment': 'run myop1',
                },
            },
        },

        'mybase2': {
            'base_urls': ['https://myhost1.abc.com:9102', 'https://myhost2.abc.com:9102'],
            'entry': tpsup.swaggertools.get_entry_by_method_suburl,
            'op': {
                'myop2_1': {
                    'num_args': 2,
                    'sub_url': 'app2/api/run_myop2/{{A0}}/{{A1}}',
                    'Accept': 'text/xml',
                    'comment': 'run myop2_1',
                    'test_str': ['my_arg0 my_arg1', 'your_arg0 your_arg1'],
                },
            },
        },
    },
}


def swagger_test_validator(a, cfg):
    if 'hello' in a:
        print(f'validating {a}: matched hello')
        return 1
    else:
        print(f'validating {a}: not matched hello')
        return 0
