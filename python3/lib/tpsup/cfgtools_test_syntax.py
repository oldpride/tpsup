import types
from typing import Union


our_syntax = {
    '^/$': {
        'cfg': {'type': dict, 'required': 1},
        'package': {'type': str},
        'minimal_args': {'type': int},
    },

    '^/cfg/([^/]+?)/$': {
        'base_urls': {'type': list, 'required': 1},
        'op': {'type': dict, 'required': 1},
        'entry': {'type': str},
        'entry_func': {'type': Union[str, types.CodeType, types.FunctionType]},
    },
    '^/cfg/([^/]+?)/op/([^/]+?)/$': {
        'sub_url': {'type': str, 'required': 1},
        'num_args': {'type': int, 'pattern': r'^\d+$'},
        'json': {'type': int, 'pattern': r'^\d+$'},
        'method': {'type': str, 'pattern': r'^(GET|POST|DELETE)$'},
        'Accept': {'type': str},
        'comment': {'type': str},
        'validator': {'type': str},
        'post_data': {'type': str},
        'test_str': {'type': list},
    },
}
