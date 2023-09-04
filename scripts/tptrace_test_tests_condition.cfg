#!/usr/bin/env perl

use strict;
use warnings;
use File::Basename;

our $our_cfg;
our %known;

# don't add 'my' in front of below because the variable is declared in the caller.
$our_cfg = {
   cfg_by_entity => {
      test_tests => {
         method => 'code',
         code => '
            update_knowledge("DUMMY", "DUM");
         ',
         tests => [
            {
                # with successful condition
                condition => '1==1',
                test => '2==2',
                if_success => 'update_ok(   "test1   expected OK")',
                if_failed  => 'update_error("test1 unexpected failure")',
            },
            {
                # with failed condition, this test shouldn't run
                condition => '1==0', 
                test => '2==2',
                if_success => 'update_ok(   "test2 unexpected OK")',
                if_failed  => 'update_error("test2 unexpected failure")',
            },
            {
                # without condition
                test => '2==2',
                if_success => 'update_ok(   "test3   expected OK")',
                if_failed  => 'update_error("test3 unexpected failure")',
            },
         ],
         AllowZero=>1,
      },
   },
   
   extra_keys => ['example' ],

   alias_map => {
   },
   
   # trace entities in this order
   trace_route => [ 
      'test_tests', 
   ],

   usage_example => <<"EOF",

   {{prog}} ANY

EOF

};

