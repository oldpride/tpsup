#!/usr/bin/env python3

import tpsup.env
import os

# convert above to python
our_cfg = {
    # global vars

    # only vars in double curlies {{ }} willl be substituted. this leaves
    # single curly, like $known{YYYYMMDD}, be eval()'ed.
    # use array to enforce sequencing because later var may rely on earlier var.
    'vars': [
        # resolve a variable now
        'TPSUP', 'os.environ["TPSUP"]',

        # 'value' is an expression, therefore, needs two different quotes if it is a string.
        'dummy_global_var2', '"hardcoded string"',

        # use single quote to delay their execution. they will be eval'ed later.
        'dummy_global_var3', 'get_log_example(known["YYYYMMDD"], known)',

        # refer to a previous var
        'dummy_global_var4', '"this is a {{dummy_global_var2}}"',
    ],

    'key_pattern': {
        # this key is a known's key. if known key is not defined, the pattern
        # will be used in place
        'ORDERID': '.+?',
        'TRADEID': '.+?',
        'BOOKID': '.+?',
        'SID': '.+?',
        'FILLEDQTY': {'pattern': '[0-9.]+'},
        'TRADEQTY': {'pattern': '[0-9.]+'},
    },

    'cfg_by_entity': {
        'test_code': {
            'method': 'code',

            # method 'code' has no method_cfg as all its implementation
            # is in 'code' below, which is part of default process
            'code': '''
                update_knowledge("DUMMY", "DUM from entity={{entity}}")
                print(f"access from entity={{ENTITY}} code, known={known}")
                if 'SECURITY' in known:
                    print(f"SECURITY={known['SECURITY']}")
                ''',
            'AllowZero': 1,
        },

        'app_cmd_pipe': {

            'method': 'cmd',

            'vars': [
                'log', '"{{TPSUP}}/tptrace_test.log"',
            ],

            'method_cfg': {
                'type': 'pipe',

                'value': [
                    # tpgrepl extended "grep -l" by allowing multiple patterns.
                ],
            },
        },

        'orders': {
            'method': 'db',
            'method_cfg': {
                'db': 'tptest@tpdbmysql',
                'db_type': 'mysql',
                'where_clause': {
                    'ORDERID': 'orderid',
                    'SID': 'sid',
                    'ORDERQTY': {'column': 'orderqty', 'numeric': 1},
                    'LASTQTY': {'column': 'lastqty', 'numeric': 1},
                    'FILLEDQTY': {'column': 'filledqty', 'numeric': 1},
                    'SENDERCOMP': 'SenderComp',
                    'TARGETCOMP': 'TargetComp',
                    'YYYYMMDD': {'clause': "CAST(LastUpdateTime as DATE) = '{{opt_value}}'",
                                 'update_knowledge': 0,
                                 # update_knowledge is an expression
                                 # eg. update_knowledge=>'{{new_value}} != 0',
                                 },
                },
                'order_clause': 'order by LastUpdateTime',

                # this only works for today
                # example_clause => "OrderDate > CAST(GETDATE() as DATE) and Status = 'Filled'",
                'example_clause': "CAST(LastUpdateTime as DATE) = '{{yyyymmdd}}'",
            },
            'comment': "comment from entity={{entity}}.\n",
        },
    },

    'extra_keys': ['example', 'security', 'YYYYMMDD'],

    'alias_map': {
        'sec': 'security',
    },

    'extend_key_map': [
        # one key's knowledge can extend to other keys.
        #    for example, if I know SEDOL, I will know CUSIP.
        # use a array to enforce the order.
        # extender function, first arg is ref to $known, second arg is new value
        # ['SECURITY', 'update_security_knowledge'],
        # ['SEDOL', 'update_security_knowledge'],
    ],

    'entry_points': [
        # use a array to enforce the order
        # known keys => table list
        # [['BOOKID'], ['booking', 'trades']],
        # [['TRADEID'], ['trades']],
        # [['ORDERID'], ['orders']],
        # [['SID', 'QTY'], ['orders']],
        # [[], ['orders']],  # this is default
    ],

    # trace entities in this order
    'trace_route': [
        # 'test_code',
        {'entity': 'orders', 'condition': '"YYYYMMDD" in known'},


        # below are untested
        # 'app_cmd_pipe',
        # {'entity': 'trades', 'AllowZero': 1},
        # 'booking',
        # 'actions',
        # {'entity': 'orders',

    ],

}

# this should be site-spec functions


def get_log_example(arg1, known):
    print(f'get_log_example() get knowledge={known}')
    print(f'get_log_example() arg1={arg1}')

    import os
    TPSUP = os.environ.get('TPSUP')
    log = f'{TPSUP}/scripts/tptrace_test.log'
    return log
