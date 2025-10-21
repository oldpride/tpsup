#!/usr/bin/env perl

use strict;
use warnings;
# use TPSUP::SWAGGER qw();
use Carp;

# however, if the validator is a string to eval, the eval will be in TPSUP::SWAGGER namespace.
# therefore, we need to specify the namespace explicitly.
sub TPSUP::SWAGGER::is_Cusip {
   my ($string) = @_;

   if ( $string =~ /^[A-Z0-9]{9}$/ ) {
      print "is_Cusip($string): matched\n";
      return 1;
   } else {
      print "is_Cusip($string): not matched\n";
      return 0;
   }
}

# the current namespace is TPSUP::BATCH, not TPSUP::SWAGGER.
# if validator is a sub, we don't need to specify the namespace.
sub swagger_test_validator {
   my ( $a, $cfg ) = @_;

   # $a is the array ref of the arguments

   if ( $a->[0] =~ /hello/ ) {
      print "validating @$a: matched hello\n";
      return 1;
   } else {
      print "validating @$a: not matched hello\n";
      return 0;
   }
}

# don't add 'my' in front of below because the variable is declared in the caller.
our $our_cfg = {
   # position_args => [ 'base', 'op' ],
   minimal_args => 2,

   extra_args => {
      'nojson' => 'nojson',    # -nojson
   },

   pre_checks => [
      # you need this in corporate network
      #{
      #   check      => 'exists($ENV{HTTPS_CA_DIR})',
      #   suggestion => 'run: export HTTPS_CA_DIR=/etc/ssl/certs',
      #},
   ],

   package => 'TPSUP::SWAGGER',
   # runs TPSUP::SWAGGER::tpbatch_code() by default

   # usage_example => "",   # usage_example's default is in package SWAGGER.pm

   # sub_url vs sub_ui
   #    sub_url is to be used by curl command
   #    sub_ui  is user interface where use manually click swagger menu on web portal.
   # sub_ui is default to share the first part of sub_url, example
   #    sub_url: app1/api/run_myop1_1
   #    sub_ui : app1/swagger-ui
   # we use default sub_ui below

   cfg => {
      mybase1 => {
         base_urls => ['https://myhost1.abc.com:9100'],
         entry     => 'swagger-tian1',
         op        => {
            myop1_1 => {
               num_args  => 1,
               sub_url   => 'app1/api/run_myop1_1',
               json      => 1,
               method    => 'POST',
               post_data => '{{A0}}',

               # eval a function defined in another module, just prefix it.
               validator => "'{{A0}}' =~ /hello/ && TPSUP::DATE::get_yyyymmdd() =~ /^20/",
               comment   => 'myop1_1',
               # json requires double string for its strings.
               # therefore, we use single quote in data.
               # however, windows cmd also uses double quote for grouping,
               # so we need to escape json's double quote with backslash.
               test_str => [ '{"hello world"}', 'abc' ],    # two tests here
            },
            myop1_2 => {
               num_args  => 1,
               sub_url   => 'app1/api/run_myop1_2',
               json      => 1,
               method    => 'POST',
               post_data => qq(['hard coded']),
               # eval a function defined in this module.
               # because eval() is called from TPSUP::SWAGGER::swagger(), therefore,
               # it is in TPSUP::SWAGGER namespace.
               # is_Cusip() is defined in this module, therefore, it is in
               # TPSUP::SWAGGER namespace.
               # So we need to prefix is_Cusip() with tpsup.batch, so that eval() can find it.
               # 'validator': "TPSUP::SWAGGER::is_Cusip('{{A0}}')",
               # after we used "sub TPSUP::SWAGGER:is_Cusip{...}" we can use
               validator => 'is_Cusip("{{A0}}")',
               comment   => 'run myop1',
               test_str  => [ '123456789', '12345' ],
            },
            myop1_3 => {
               num_args => 1,
               sub_url  => 'app1/api/run_myop1_3/{{A0}}',
               # TPSUP::BATCH sources this file,
               # therefore, the current namespace is TPSUP::BATCH, not TPSUP::SWAGGER.
               # functions defined in this file doen't need to prefix with TPSUP::BATCH.
               validator => \&swagger_test_validator,
               comment   => 'run myop1',
               test_str  => [ 'hello', 'world' ],
            },
         },
      },

      mybase2 => {
         base_urls => [ 'https://myhost1.abc.com:9102', 'https://myhost2.abc.com:9102' ],
         # this file is sourced by TPSUP::BATCH, so the working namespace is TPSUP::BATCH.
         # therefore, we need to specify TPSUP::SWAGGER explicitly.
         entry => \&TPSUP::SWAGGER::get_entry_by_method_suburl,
         op    => {
            myop2_1 => {
               num_args => 2,
               sub_url  => 'app2/api/run_myop2/{{A0}}/{{A1}}',
               accept   => 'text/xml',
               comment  => 'run myop2_1',
               test_str => [ 'hello world', qq("donn't" answer) ],
            },
            myop2_2 => {
               num_args  => '*',
               sub_url   => 'app3/api/run_myop2/',
               method    => 'POST',
               post_data => 'json_array_string',
               test_str  => ['hard coded'],
            },
         },
      },
   },
};
