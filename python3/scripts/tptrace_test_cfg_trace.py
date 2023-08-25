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

        'applog_cmd_grep_keys': {
            'method': 'cmd',
            'vars': [
                'log', '"{{cfgdir}}/tptrace_test.log"',
            ],

            'method_cfg': {
                'type': 'grep_keys',
                # if key is in known, use its value to grep.
                'value': [
                    'TRADEID',
                    {'key': 'ORDERID', 'pattern': 'orderid={{opt_value}}'},
                    'BOOKID',
                ],
                'file': '"{{log}}"',
                'logic': 'AND',
            },
            'tail': 5,
            'tests': [
                {
                    'test': 'row_count > 0',
                    'if_success': 'update_ok(   "seen TRANSACTION in {{log}}");',
                    'if_failed': 'update_error(  "no TRANSACTION in {{log}}");',
                },
            ],
            'comment': 'test using grep_keys to generate command',
        },

        'applog_cmd_pipe': {
            'method': 'cmd',
            'vars': [
                'log', '"{{cfgdir}}/tptrace_test.log"',
            ],

            'method_cfg': {
                'type': 'pipe',
                # 2D array,
                #    outer loop is connected by pipe
                #    inner loop is for OR logic for grep command.
                #
                # method_cfg => {
                #    type  => 'pipe',
                #    value => [
                #       ['grep=grep -E', 'OR11', 'OR12'],
                #       ['grep=grep -v -E', 'OR21', 'OR22'],
                #       ['grep=grep -E ',   'OR31', 'OR32'],
                #       ['cmd=grep -v -E "{{JUNK1=j1}}|{{JUNK2=j2}}"'],
                #       ['cmd=tail -10'],
                #    ],
                #    file => 'app.log',
                # },
                #
                #  if only $known{OR11}, $known{OR12}, $known{OR21} are defined, this will generate
                #    grep -E '{{OR11}}|{{OR12}}' app.log |grep -v -E '{{OR21}}'|grep -v "j1|j2"|tail -10
                #
                #  other value:
                #      ['tpgrepl=tpgrepl', 'TRADEID|ORDERID', 'x=BOOKID'],

                'value': [
                    ['grep=tpgrep', 'TRADEID', 'ORDERID'],
                    ['grep=tpgrep -v', 'BOOKID'],
                    ['cmd=tpgrep -v "{{JUNK=junk1}}|{{JUNK=junk2}}"'],
                ],
                'file': '{{log}}',
            },
            'top': 5,
            # 'AllowZero': 0,
            'AllowMultiple': 1,
            'tests': [
                {
                    'test': 'row_count > 0',
                    'if_success':   'update_ok("pipe: seen TRANSACTION in {{log}}");',
                    'if_failed': 'update_error("pipe:   no TRANSACTION in {{log}}");',
                },
            ],

            'comment': 'test using pipe to generate command',
        },

        'applog_cmd_post_code': {
            'method': 'cmd',
            'vars': [
                'log', '"{{cfgdir}}/tptrace_test.log"',
            ],

            'method_cfg': {
                'type': 'cmd',
                'value': 'tpgrep -E " (ERROR|FAIL)[ :]" {{log}}',
            },

            'top': 5,

            'post_code': '''
                if row_count > 0:
                    update_error("seen ERROR in {{log}}")
                    print(f"access from entity={{ENTITY}}")
            ''',
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

        'applog_log': {
            'method': 'log',
            'method_cfg': {
                'log': '"{{cfgdir}}/tptrace_test.log"',
                # named groups
                # https://docs.python.org/3/library/re.html#regular-expression-syntax
                # https://stackoverflow.com/questions/10059673
                'extract': 'tradeid=(?P<TRADEID>{{pattern::TRADEID}}),.*?sid=(?P<SID>{{pattern::SID}}),.*?bookid=(?P<BOOKID>{{pattern::BOOKID}}),.*?qty=(?P<TRADEQTY>{{pattern::TRADEQTY}}),',
            },
            'update_key': {
                'BOOKID': 'BOOKID',
                'TRADEID': 'TRADEID',
                'SID': 'SID',
                'TRADEQTY': {'column': 'TRADEQTY', 'numeric': 1},
            },
        },

        'applog_section': {
            'method': 'section',
            'method_cfg': {
                'log': '"{{cfgdir}}/tptrace_test_section*.log"',

                # PreMatch/PreExclude are tried before BeginPattern/EndPattern are tried
                # they are for speedup, it covers every line, therefore, be careful to
                # avoid filtering out BeginPattern/EndPattern.
                'PreMatch': '^2021',
                # PreExclude => '^2022',

                # this cfg will transferred to TPSUP::LOG::get_log_sections() sub
                'BeginPattern': 'section id .*? started',
                'EndPattern': 'section completed',

                # PostPattern/PostPattern are tried after BeginPattern/EndPattern are tried
                # they are also for speed-up
                'PostMatch': 'order id|trade id',
                # PostExclude => 'no content',

                'ExtractPatterns': [
                    '^(?P<BeginTime>.{23}) section id (?P<SectionId>.*?) started',
                    '^(?P<EndTime>.{23}) section completed',
                    'order id (?P<OrderId>\S+)',
                    'trade id (?P<TradeId>\S+)',
                ],
                'KeyType': {'OrderId': 'Array', 'TradeId': 'Hash'},

                # use csv_filter below for consistency
                # ItemMatchExp can use {{...}} vars. this is applied after a whole section is
                # completed.
                # 'ItemMatchExp': '"TRD-0002" in r["TradeId"]'
                # ExcludeExp =>'...',

            },

            'csv_filters': [
                {
                    'condition': '1',
                    'MatchExps': ['"TRD-0002" in r["TradeId"]'],
                    'ExcludeExps': ['"ORD-0001" in r["OrderId"]'],
                },
            ],

            'update_key': {
                # the key is $known key. The column is the the key of a section
                'SECTION_BEGINTIME': {'column': 'BeginTime'},
                'SECTION_ENDTIME': {'column': 'EndTime'},
                'SECTIONID': {'column': 'SectionId'},
                'ORDERIDS': {'column': 'OrderId'},
                'ORDERID2': {'code': 'r["OrderId"][0]', 'condition': 'r["OrderId"]'},
            },

            'comment': 'test entity={{entity}}',
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
        'applog_cmd_grep_keys',
        'applog_cmd_pipe',
        'applog_cmd_post_code',
        'applog_log',
        'applog_section',
    ],

    'usage_example':  '''
    {{prog}} example=orders yyyymmdd=20211129
    
    # test all entitiesclear
    {{prog}} sec=IBM orderqty=4,500 tradeqty=400 yyyymmdd=20211129

    # test actions
    {{prog}} -t actions orderid=ORD-0001

    # test applog_cmd_grep_keys
    {{prog}} -t applog_cmd_grep_keys orderid=ORD-0001 tradeid=TRD-0002 bookid=BKG-0002

    # test applog_cmd_grep_keys
    {{prog}} -t applog_cmd_pipe orderid=ORD-0001 tradeid=TRD-0002 bookid=BKG-0002

    # test applog_cmd_post_code
    {{prog}} -t applog_cmd_post_code orderid=ORD-0001 

    # test applog_log
    {{prog}} -t applog_log bookid=BKG-0002 sid=400001 TRADEID=TRD-0002 TRADEQTY=400
    {{prog}} -t applog_log any

    # test applog_section
    {{prog}} -t applog_section bookid=BKG-0002 sid=400001 TRADEID=TRD-0002 TRADEQTY=400
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
