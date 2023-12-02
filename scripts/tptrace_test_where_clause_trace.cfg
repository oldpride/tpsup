#!/usr/bin/env perl

use strict;
use warnings;

# 'our' can be used multiple times. Using it here allows us to use 'strict' and 'warning'
# to check this cfg file alone, as
#     $ perl tptrace_test.cfg
our %known;

# don't add 'my' in front of below because the variable is declared in the caller.
our $our_cfg = {
   cfg_by_entity => {
      orders => {
         method => 'db',
         method_cfg=>{
            db => 'tptest@tpdbmysql',
            db_type => 'mysql',
            where_clause => {
               ORDERID => 'orderid',
               SID  => 'sid',
               ORDERQTY => {
                  if_exp      => '$known{USER_DATA}',
                  clause      => 'orderqty = {{USER_DATA}}',
                  else_clause => 'orderqty = {{opt_value}}',
                  numeric=>1
               },
               YYYYMMDD  => { clause=>"CAST(LastUpdateTime as DATE) = '{{opt_value}}'",
                              update_knowledge=>0,
                            },
            },
            order_clause => 'order by LastUpdateTime',
      
            example_clause => "CAST(LastUpdateTime as DATE) = '{{yyyymmdd}}'",
         },

         comment => "comment from entity={{entity}}.\n",
      },
   },
   
   extra_keys => ['example', 'security', 'sedol', 'cusip', 'isin', 'user_data'],

   alias_map => {
      sec => 'security',
      oid => 'orderid',
   },
   
   extend_key_map => [ 
      # one key's knowledge can extend to other keys.
      #    for example, if I know SEDOL, I will know CUSIP.
      # use a array to enforce the order.
      # extender function, first arg is ref to $known, second arg is new value
      [ 'SECURITY', \&update_security_knowledge ],
      [ 'SEDOL',    \&update_security_knowledge ],
      [ 'CUSIP',    \&update_security_knowledge ],
      [ 'ISIN',     \&update_security_knowledge ],
      [ 'SID',      \&update_security_knowledge ],
   ],

   trace_route => [ 
      'orders', 
   ],

   usage_example => <<"EOF",
   # load test database
   sql tptest\@tpdbmysql file tptrace_test_db.sql 

   {{prog}} yyyymmdd=20211129 sec=IBM orderqty=4,500
   {{prog}} yyyymmdd=20211129 sec=IBM orderqty=4,500 user_data=999

EOF

};

# this should be site-spec functions
use TPSUP::TRACER_test_sitespec qw(update_security_knowledge); 

