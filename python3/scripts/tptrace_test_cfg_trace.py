#!/usr/bin/env python3

from pprint import pformat
import tpsup.env
import os
from tpsup.tracer_test_sitespec import update_security_knowledge

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
                'db': 'tptest@tpdbmssql',
                'db_type': 'mssql',
                # 'db': 'tptest@tpdbmysql',
                # 'db_type': 'mysql',
                'where_clause': {
                    'ORDERID': 'orderid',
                    'SID': 'sid',
                    'ORDERQTY': {'numeric': 1, 'clause': "orderqty <= {{opt_value}}"},
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

        'trades': {
            'method': 'db',
            'method_cfg': {
                'db': 'tptest@tpdbmssql',
                'db_type': 'mssql',
                'where_clause': {
                    # one order can have multiple trades
                    'TRADEID': 'tradeid',
                    'ORDERID': 'orderid',
                    'SID': 'sid',
                    'ORDERQTY': {'column': 'qty',
                                 'numeric': 1,
                                 'clause': "qty <= {{opt_value}}",
                                 'update_knowledge': 0,
                                 },
                    'FILLEDQTY': {'column': 'qty',
                                  'numeric': 1,
                                  'clause': "qty <= {{opt_value}}",
                                  'update_knowledge': 0,
                                  },
                    'TRADEQTY': {'column': 'qty', 'numeric': 1, },
                    'TRADEPRICE':  {'column': 'Price', 'numeric': 1},
                    'TARGETCOMP': 'TargetComp',
                    'YYYYMMDD': {'clause': "CAST(TradeDate as DATE) = '{{opt_value}}'",
                                 'update_knowledge': 0,
                                 }
                },
                'order_clause': 'order by LastUpdateTime',
                'example_clause': "TradeDate >= '{{yyyy}}{{mm}}{{dd}}'",
            },
            'comment': "comment from entity={{entity}}.\n",
        },

        'actions': {
            'method': 'db',
            'method_cfg': {
                'db': 'tptest@tpdbmssql',
                'db_type': 'mssql',
                'where_clause': {
                    # one order can have multiple trades
                    'ORDERID': 'msgid',
                    'FILLEDQTY': {'column': 'filledqty', 'numeric': 1},
                },
                # order_clause => 'order by LastUpdateTime',
                # example_clause => "TradeDate >= '{{yyyy}}{{mm}}{{dd}}'",
                # Id,MsgId,STATUS,FilledQty
                # 1,ORD-0001,,
                # 2,ORD-0001,SENT,
                # 3,ORD-0001,PARTIAL,600
                # 4,ORD-0001,COMPLETED,1000
            },
            'csv_filters': [
                {
                    'condition': '2==1+1',
                    'ExportExps': [
                        # use ternary operator to make kv pair.
                        'weight=0 if r["STATUS"] == "COMPLETED" else 1 if r["STATUS"] == "PARTIAL" else 2',
                    ],
                    'SortKeys': ['weight'],
                },
            ],
            'comment': 'trace in trades table',
            'AllowMultiple': 1,
            'top': 1,
            # to test:
            #     tptrace_test -t actions orderid=ORD-0001
        },

        'booking': {
            'method': 'db',
            'method_cfg': {
                'db': 'tptest@tpdbmssql',
                'db_type': 'mssql',
                'template': """
                    -- this is on purpose convoluted to show how template is used in complex query
                    select * from (
                          select * from booking (nolock) bk
                            where  1=1
                                      {{where::YYYYMMDD}}
                                        {{where::SID}}
                    ) as BookingByTradeDateSid
                    where 1=1
                        {{where::BOOKID}}
                        {{where::TRADEID}}
                        {{where::ORDERID}}
                        {{where::TRADEPRICE}}
                        {{where::ORDERQTY}}
                        {{where::TRADEQTY}}
                        {{where::TARGETCOMP}}
                    """,
                'where_clause': {
                    # one order can have multiple trades
                    'TRADEID': 'tradeid',
                    'BOOKID': 'bookid',
                    'ORDERID': 'orderid',
                    'ORDERQTY': {'numeric': 1, 'clause': "OrderQty = {{opt_value}}"},
                    'TRADEQTY': {'column': 'qty', 'numeric': 1, },
                    'TRADEPRICE':  {'column': 'Price', 'numeric': 1},
                    'TARGETCOMP': 'TargetComp',

                    # these two has table prefix
                    'SID': 'bk.sid',
                    'YYYYMMDD': {'clause': "CAST(bk.TradeDate as DATE) = '{{opt_value}}'",
                                 'update_knowledge': 0,
                                 },
                },
                'order_clause': 'order by LastUpdateTime',
                'example_clause': "TradeDate = '{{yyyymmdd}}'",
            },
        },
    },

    'extra_keys': ['example', 'security', 'YYYYMMDD'],

    'alias_map': {
        'sec': 'security',
        'oid': 'orderid',
        'tid': 'tradeid',
    },

    'extend_key_map': [
        # one key's knowledge can extend to other keys.
        #    for example, if I know SEDOL, I will know CUSIP.
        # use a array to enforce the order.
        # extender function, first arg is ref to $known, second arg is new value
        ['SECURITY', update_security_knowledge],
        ['SEDOL', update_security_knowledge],
    ],

    'entry_points': [
        # use a array to enforce the order
        # known keys => table list
        [['BOOKID'], ['booking', 'trades']],
        [['TRADEID'], ['trades']],
        [['ORDERID'], ['orders']],
        # [['SID', 'QTY'], ['orders']],
        # [[], ['orders']],  # this is default
    ],

    # trace entities in this order
    'trace_route': [
        'test_code',
        {'entity': 'orders', 'condition': '"YYYYMMDD" in known'},
        {'entity': 'trades', 'AllowZero': 1},
        'actions',
        'booking',

        # below are untested
        # 'app_cmd_pipe',


    ],

    'usage_example':  '''
    {{prog}} example=orders yyyymmdd=20211129
    
    {{prog}} sec=IBM orderqty=4,500 tradeqty=400 yyyymmdd=20211129

    {{prog}} -t actions orderid=ORD-0001
    ''',
}

# this should be site-spec functions


def get_log_example(arg1, known):
    print(f'get_log_example() get knowledge={pformat(known)}')
    print(f'get_log_example() arg1={arg1}')

    import os
    TPSUP = os.environ.get('TPSUP')
    log = f'{TPSUP}/scripts/tptrace_test.log'
    return log
