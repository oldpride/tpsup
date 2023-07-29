#!/usr/bin/env python3

# #!/usr/bin/env perl

# use strict;
# use warnings;

# # 'our' can be used multiple times. Using it here allows us to use 'strict' and 'warning'
# # to check this cfg file alone, as
# #     $ perl tptrace_test.cfg
# our %known;

# # don't add 'my' in front of below because the variable is declared in the caller.
# our $our_cfg = {
#    # global vars

#    # vars is an array of key=>value pairs

#    # only vars in double curlies {{ }} willl be substituted. this leaves
#    # single curly, like $known{YYYYMMDD}, be eval()'ed.

#    # use array to enforce sequencing because later var may rely on earlier var.

#    vars => [
#       # the following is equivalent to `date`+chomp(). but chomp(`date`) does't work.
#       dummy_global_var1 => 'cmd_output_string("date")',

#       # 'value' is an expression, therefore, needs two different quotes if it is a string.
#       dummy_global_var2 => '"hardcoded string"',

#       # use single quote to delay their execution. they will be eval'ed later.
#       dummy_global_var3 => 'get_log_example($known{YYYYMMDD}, \%known)',

#       dummy_global_var4 => '"this is a {{dummy_global_var2}}"',
#    ],

#    key_pattern => {
#       # this key is a %known key. if %known key is not defined, the pattern
#       # will be used in place
#       ORDERID   => '.+?',
#       TRADEID   => '.+?',
#        BOOKID   => '.+?',
#       SID       => '.+?',
#       FILLEDQTY => {pattern=>'[0-9.]+'},
#        TRADEQTY => {pattern=>'[0-9.]+'},
#    },

#    cfg_by_entity => {
#       test_code => {
#          method => 'code',

#          # method 'code' has no method_cfg as all its implementation is in 'code'
#          # below, which is part of default process
#          code => q(
#             update_knowledge("DUMMY", "DUM from entity={{entity}}");
#             print "access from entity={{ENTITY}} code, known=", Dumper(\%known);
#          ),
#          AllowZero => 1,
#       },

#       # where_clause key is $opt/$known key, value is table's column name
#       # $opt and $known should use the same key:
#       #     $known is upper case, in order to make command args easier.
#       #     therefore $opt is upper case too, in order to be consistent

#       orders => {
#          method => 'db',
#          method_cfg=>{
#             db => 'tptest@tpdbmysql',
#             db_type => 'mysql',
#             where_clause => {
#                ORDERID => 'orderid',
#                SID  => 'sid',
#                ORDERQTY => {column=>'orderqty',numeric=>1},
#                LASTQTY => {column=>'lastqty',numeric=>1},
#                FILLEDQTY => {column=>'filledqty',numeric=>1},
#                SENDERCOMP  => 'SenderComp',
#                TARGETCOMP  => 'TargetComp',
#                YYYYMMDD  => { clause=>"CAST(LastUpdateTime as DATE) = '{{opt_value}}'",
#                               update_knowledge=>0,
#                               # update_knowledge is an expression
#                               # eg. update_knowledge=>'{{new_value}} != 0',
#                             },
#             },
#             order_clause => 'order by LastUpdateTime',

#             #this only works for today
#             #example_clause => "OrderDate > CAST(GETDATE() as DATE) and Status = 'Filled'",
#             example_clause => "CAST(LastUpdateTime as DATE) = '{{yyyymmdd}}'",
#          },

#          comment => "comment from entity={{entity}}.\n",
#       },

#       trades => {
#          method => 'db',
#          method_cfg=>{
#             db => 'tptest@tpdbmssql',
#             db_type => 'mssql',
#             where_clause => {
#                # one order can have multiple trades
#                TRADEID => 'tradeid',
#                ORDERID => 'orderid',
#                SID  => 'sid',
#                ORDERQTY => {column=>'qty',
#                             numeric=>1,
#                             clause => "qty <= {{opt_value}}",
#                             update_knowledge=>0,
#                            },
#                FILLEDQTY => {column=>'qty',
#                             numeric=>1,
#                             clause => "qty <= {{opt_value}}",
#                             update_knowledge=>0,
#                            },
#                 TRADEQTY => {column=>'qty', numeric=>1,},
#               TRADEPRICE =>  {column=>'Price', numeric=>1},
#               TARGETCOMP => 'TargetComp',
#                 YYYYMMDD => { clause=>"CAST(TradeDate as DATE) = '{{opt_value}}'",
#                               update_knowledge=>0,
#                             }
#             },
#             order_clause => 'order by LastUpdateTime',
#             example_clause => "TradeDate >= '{{yyyy}}{{mm}}{{dd}}'",
#          },
#          comment => "comment from entity={{entity}}.\n",
#       },

#       actions => {
#          method => 'db',
#          method_cfg =>{
#             db => 'tptest@tpdbmssql',
#             db_type => 'mssql',
#             where_clause => {
#                # one order can have multiple trades
#                ORDERID => 'msgid',
#                FILLEDQTY => { column=>'filledqty', numeric=>1},
#             },
#             #order_clause => 'order by LastUpdateTime',
#             #example_clause => "TradeDate >= '{{yyyy}}{{mm}}{{dd}}'",
#             # Id,MsgId,STATUS,FilledQty
#             # 1,ORD-0001,,
#             # 2,ORD-0001,SENT,
#             # 3,ORD-0001,PARTIAL,600
#             # 4,ORD-0001,COMPLETED,1000
#          },
#          csv_filter => [
#             [
#               [ ], # depending keys, like entry_points
#               {
#                ExportExps => [
#                   'weight=$STATUS eq "COMPLETED" ? 0 : $STATUS eq "PARTIAL" ? 1 : 2',
#                   ],
#                 SortKeys => [ 'weight' ],
#               },
#             ]
#          ],
#          # csv_filter => {
#          #   ExportExps => [
#          #      'weight=$STATUS eq "COMPLETED" ? 0 : $STATUS eq "PARTIAL" ? 1 : 2',
#          #      ],
#          #   SortKeys => [ 'weight' ],
#          # },
#          comment => 'trace in trades table',
#          AllowMultiple=>1,
#          top=>1,
#          # to test:
#          #     tptrace_test -t actions orderid=ORD-0001
#       },

#       booking => {
#          method => 'db',
#          method_cfg=>{
#             db => 'tptest@tpdbmssql',
#             db_type => 'mssql',
#             template => "
#                -- this is on purpose convoluted to show how template is used in complex query
#                select * from (
#                   select * from booking (nolock) bk
#                   where  1=1
#                          {{where::YYYYMMDD}}
#                          {{where::SID}}
#                ) as BookingByTradeDateSid
#                where 1=1
#                      {{where::BOOKID}}
#                      {{where::TRADEID}}
#                      {{where::ORDERID}}
#                      {{where::TRADEPRICE}}
#                      {{where::ORDERQTY}}
#                      {{where::TRADEQTY}}
#                      {{where::TARGETCOMP}}
#             ",
#             where_clause => {
#                # one order can have multiple trades
#                TRADEID => 'tradeid',
#                ORDERID => 'orderid',
#                BOOKID => 'bookid',
#                ORDERQTY => {numeric=>1, clause=>"qty <= {{opt_value}}", update_knowledge=>0},
#                TRADEQTY => {column=>'qty', numeric=>1,},
#              TRADEPRICE =>  {column=>'Price', numeric=>1},
#              TARGETCOMP => 'TargetComp',

#                    # these two has table prefix
#                    SID  => 'bk.sid',
#                YYYYMMDD => { clause=>"CAST(bk.TradeDate as DATE) = '{{opt_value}}'",
#                               update_knowledge=>0,
#                            },
#             },
#             order_clause => 'order by LastUpdateTime',
#             example_clause => "TradeDate = '{{yyyymmdd}}'",
#          },
#       },

#       applog_cmd_extract => {
#          method => 'cmd',

#          condition=>'$known{TRADEID}',

#          vars => [
#             log => '"{{cfgdir}}/tptrace_test.log"',
#          ],

#          method_cfg => {
#             type    => 'cmd',
#             value   => 'zgrep -E {{TRADEID}} {{log}}',
#             example => "zgrep -E orderid= {{log}}|head -n 5",
#             # zgrep -E, handle both regular and gzipped files with RegExp

#             # Perl uses (?<NAME>pattern) to specify names captures. You have to use the %+
#             # hash to retrieve them.
#             #   $variable =~ /(?<count>\d+)/;
#             #   print "Count is $+{count}";
#             extract => 'orderid=(?<ORDERID>{{pattern::ORDERID}}),.*tradeid=(?<TRADEID>{{pattern::TRADEID}}),.*sid=(?<SID>{{pattern::SID}}),.*filledqty=(?<FILLEDQTY>{{pattern::FILLEDQTY}}),',
#          },

#          tests => [
#             {
#                test => '$row_count > 0',
#                if_success => '
#                   # two ways to update
#                   update_knowledge("LOGGED_TRANSACTION", 1);
#                   $known{DUMMY_KNOWLEDGE} = $row_count+1;
#                ',
#             },
#             {
#                test => '$rc == 0',
#                if_failed => 'exit(1);',
#             },
#          ],

#          update_key => {
#                  ORDERID => 'ORDERID',
#                  TRADEID => 'ORDERID',
#                      SID => 'SID',
#                FILLEDQTY => {column=>'FILLEDQTY', numeric=>1},
#          },

#          comment => 'test extract',
#       },

#       applog_cmd_grep_keys => {
#          method => 'cmd',

#          vars => [
#             log => '"{{cfgdir}}/tptrace_test.log"',
#          ],

#          method_cfg => {
#             type  => 'grep_keys',

#             value => [
#                'TRADEID',
#                {key=>'ORDERID', pattern=>'orderid={{opt_value}}'},
#                'BOOKID',
#             ],
#             file => '"{{log}}"',
#             logic=>'AND',  # default to OR
#             # grep => 'zgrep -E',    # this is default
#             # grep => 'zgrep -E -l', # for massive output, print only file names.
#             example => "zgrep -E 'orderid=' {{log}}",
#          },
#          tail => 5, # 'tail' overrides 'top'
#          tests => [
#             {
#                test => '$row_count > 0',
#                if_success => 'update_ok(   "seen TRANSACTION in {{log}}");',
#                if_failed  => 'update_error(  "no TRANSACTION in {{log}}");',
#             },
#          ],
#          comment => 'test using grep_keys to generate command',
#       },

#       applog_cmd_pipe => {
#          method => 'cmd',

#          vars => [
#             log => '"{{cfgdir}}/tptrace_test.log"',
#          ],

#          method_cfg => {
#             type  => 'pipe',

#             value => [
#                ['grep=grep -E', 'TRADEID', 'ORDERID'],
#                ['grep=grep -v', 'BOOKID'],
#                ['cmd=grep -v -E "{{JUNK=junk1}}|{{JUNK=junk2}}"'],
#             ],
#             file => '{{log}}',
#          },
#          top => 5,
#          tests => [
#             {
#                test => '$row_count > 0',
#                if_success => 'update_ok(    "pipe: seen TRANSACTION in {{log}}");',
#                if_failed  => 'update_error( "pipe:   no TRANSACTION in {{log}}");',
#             },
#          ],
#          comment => 'test using pipe to generate command',
#       },

#       applog_cmd_pipe_tpgrepl => {
#          method => 'cmd',

#          vars => [
#             log => '"{{cfgdir}}/tptrace_test.log"',
#          ],

#          method_cfg => {
#             type  => 'pipe',

#             value => [
#                # tpgrepl extended "grep -l" by allowing multiple patterns.
#                # this is useful to when normal "grep" will create too much output.
#                ['tpgrepl=tpgrepl', 'TRADEID|ORDERID', 'x=BOOKID'],
#             ],
#             file => '{{log}}',
#          },
#          top => 5,
#          tests => [
#             {
#                test => '$row_count > 0',
#                if_success => 'update_ok(    "pipe_tpgrepl: seen TRANSACTION in {{log}}");',
#                if_failed  => 'update_error( "pipe_tpgrepl:   no TRANSACTION in {{log}}");',
#             },
#          ],
#          comment => 'test using pipe_tpgrepl to generate command',
#       },

#       applog_cmd_post_code => {
#          method => 'cmd',
#          vars => [
#             log => '"{{cfgdir}}/tptrace_test.log"',
#          ],

#          method_cfg => {
#             type  => 'cmd',
#             value => 'zgrep -E " (ERROR|FAIL)[ :]" {{log}}',
#          },

#          top => 5,

#          post_code => <<'END',
#             if ($row_count > 0) {
#                update_error("seen ERROR in {{log}}"),
#                print "access from entity={{ENTITY}}\n";
#             }
# END
#       },

#       applog_log =>{
#          method  => 'log', # can update knowledge

#          method_cfg => {
#             log => '"{{cfgdir}}/tptrace_test.log"',
#             # Perl uses (?<NAME>pattern) to specify names captures. You have to use the %+
#             # hash to retrieve them.
#             #   $variable =~ /(?<count>\d+)/;
#             #   print "Count is $+{count}";
#             extract => 'tradeid=(?<TRADEID>{{pattern::TRADEID}}),.*?sid=(?<SID>{{pattern::SID}}),.*?bookid=(?<BOOKID>{{pattern::BOOKID}}),.*?qty=(?<TRADEQTY>{{pattern::TRADEQTY}}),',
#          },

#          update_key => {
#             BOOKID => 'BOOKID',
#            TRADEID => 'TRADEID',
#                SID => 'SID',
#             TRADEQTY => { column => 'TRADEQTY', numeric=>1 },
#          },
#          # example is derived from key_pattern automatically
#       },

#       applog_section =>{
#          method  => 'section',

#          method_cfg => {
#             log => '"{{cfgdir}}/tptrace_test_section*.log"',

#             # PreMatch/PreExclude are tried before BeginPattern/EndPattern are tried
#             # they are for speedup, it covers every line, therefore, be careful to
#             # avoid filtering out BeginPattern/EndPattern.
#               PreMatch   => '^2021',
#             # PreExclude => '^2022',

#             # this cfg will transferred to TPSUP::LOG::get_log_sections() sub
#             BeginPattern  => 'section id .*? started',
#               EndPattern  => 'section completed',

#             # PostPattern/PostPattern are tried after BeginPattern/EndPattern are tried
#             # they are also for speed-up
#                PostMatch   => 'order id|trade id',
#             #  PostExclude => 'no content',

#             ExtractPatterns => [
#                '^(?<BeginTime>.{23}) section id (?<SectionId>.*?) started',
#                '^(?<EndTime>.{23}) section completed',
#                'order id (?<OrderId>\S+)',
#                'trade id (?<TradeId>\S+)',
#               ],
#             KeyAttr    => { OrderId=>'Array', TradeId=>'Hash' },
#             KeyDefault => { OrderId=>[],      TradeId=>{} },
#             # KeyDefault is to simplify MatchExp, allowing us to use
#             #     MatchExp =>'grep {/^ORD-0001$/}  @{$r{OrderId}}'
#             # without worrying about whether $r{OrderId} is defined.

#             # use csv_filter below for consistency
#             # MatchExp can use {{...}} vars. this is applied after a whole section is
#             # completed.
#             #MatchExp =>'grep(/^{{pattern::ORDERID}}$/, @{$r{OrderId}})',
#             # ExcludeExp =>'...',
#          },

#          csv_filter => [
#            [
#              [], # dependending keys, like entry points
#              { MatchExps => ['defined($OrderId) && grep(/{{pattern::ORDERID}}/, @$OrderId)'],}
#            ],
#          ],

#          update_key => {
#              # the key is $known key. The column is the the key of a section
#              SECTION_BEGINTIME => { column=>'BeginTime' },
#              SECTION_ENDTIME   => { column=>'EndTime'   },
#              SECTIONID         => { column=>'SectionId' },
#              ORDERIDS          => { column=>'OrderId'   },
#              ORDERID2          => { code=>'$r{OrderId}->[0]', condition=>'$r{OrderId}' },
#          },

#          comment => 'test entity={{entity}}',
#       },

#       applog_path =>{
#          method  => 'path',

#          method_cfg => {
#             paths => ['{{cfgdir}}'],
#             HandleExp => '$short =~ /tptrace_test/',    # default to 1
#             #RecursiveMax => 2,                         # depth. default to 100
#          },

#          output_key => 'short',      # use short file name to convert @hashes to %hash1

#          code => <<'END',
#             my $short = "tptrace_test.cfg";
#             if (defined $hash1{$short}) {
#                if ($hash1{$short}->[0]->{mt_string} =~ /{{YYYY}}-{{MM}}-{{DD}}/) {
#                   update_error("$short is updated today {{YYYY}}-{{MM}}-{{DD}}");
#                } else {
#                   update_ok("$short is not updated today {{YYYY}}-{{MM}}-{{DD}}. last update: $hash1{$short}->[0]->{mt_string}");
#                }
#             } else {
#                update_error("$short is not found");
#             }
# END

#          comment => 'test method=path',

#          AllowMultiple => 1,
#       },
#    },

#    extra_keys => ['example', 'security', 'sedol', 'cusip', 'isin'],

#    alias_map => {
#       sec => 'security',
#       oid => 'orderid',
#       tid => 'tradeid',
#       tc  => 'TargetComp',
#       #ts  => 'TargetSub',
#       sc  => 'SenderComp',
#       #ss  => 'SenderSub',
#    },

#    extend_key_map => [
#       # one key's knowledge can extend to other keys.
#       #    for example, if I know SEDOL, I will know CUSIP.
#       # use a array to enforce the order.
#       # extender function, first arg is ref to $known, second arg is new value
#       [ 'SECURITY', \&update_security_knowledge ],
#       [ 'SEDOL',    \&update_security_knowledge ],
#       [ 'CUSIP',    \&update_security_knowledge ],
#       [ 'ISIN',     \&update_security_knowledge ],
#       [ 'SID',      \&update_security_knowledge ],
#    ],

#    entry_points => [
#       # use a array to enforce the order
#       # known keys => table list
#       [ ['BOOKID'],     ['booking', 'trades']],
#       [ ['TRADEID'],    ['trades']],
#       [ ['ORDERID'],    ['orders']],
#       [ ['SID', 'QTY'], ['orders']],
#       [ [],             ['orders']],   # this is default
#    ],

#    # trace entities in this order
#    trace_route => [
#       'test_code',
#       #{ entity => 'orders', condition => '$known{YYYYMMDD} == $known{TODAY}'},
#       'orders',
#       { entity=>'trades', AllowZero=>1},
#       'booking',
#       'actions',
#       { entity=>'orders',
#         # normally we trace from orderid->tradeid->bookid but in case
#         # we know tradeid first, we can want to search back orders table for orderid.
#         # therefore, we set the reentry=1
#         condition => '$known{TRADEID} && !$known{ORDERID}',
#         reentry=>1,
#       },
#       'applog_cmd_extract',
#       'applog_cmd_grep_keys',
#       'applog_cmd_pipe',
#       'applog_cmd_pipe_tpgrepl',
#       'applog_cmd_post_code',
#       'applog_log',
#       'applog_section',
#       'applog_path',
#    ],

#    usage_example => <<"EOF",
#    # load test database
#    sql tptest\@tpdbmysql file tptrace_test_db.sql
#    sql tptest\@tpdbmssql file tptrace_test_db.sql

#    # get example
#    {{prog}} yyyymmdd=20211129 example=booking

#    # trace
#    {{prog}} yyyymmdd=20211129 tradeid=TRD-0001
#    {{prog}} yyyymmdd=20211129 sec=IBM orderqty=4,500 tradeqty=600 sc=BLKC

#    # force to trace through
#    {{prog}} -f yyyymmdd=20211129 tradeid=TRD-0001

#    # test table prefix in where_clause
#    {{prog}} -t booking bookid=BKG-0003 yyyymmdd=20211129

#    # test method=cmd with extract
#    {{prog}} -t applog_cmd_extract  tradeid=TRD-0001 yyyymmdd=20211129

#    # test method=section
#    {{prog}} -t applog_section yyyymmdd=20211129 orderid=ORD-0001
#    {{prog}} -t applog_section yyyymmdd=20211129 # this will complain too many matches

#    # test global vars and cfg syntax
#    {{prog}} -st all ANY

# EOF

# };

# # this should be site-spec functions
# use TPSUP::TRACER_test_sitespec qw(update_security_knowledge);

# sub get_log_example {
#    my ($arg1, $known) = @_;

#    print "get_log_example() get knowledge=" . Dumper($known);
#    print "get_log_example() arg1=$arg1\n";
#    #print __LINE__, " current namespace = ", __PACKAGE__, "\n";

#    use File::Basename;

#    my $dir = dirname(__FILE__);
#    my $log = "$dir/tptrace_test.log";

#    return $log;
# }

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
        'test_code',
        # { entity => 'orders', condition => '$known{YYYYMMDD} == $known{TODAY}'},
        # 'orders',
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
