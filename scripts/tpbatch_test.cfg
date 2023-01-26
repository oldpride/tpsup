#!/usr/bin/env perl

# test tpbatch/TPSUP::BATCH basic syntax

use strict;
use warnings;

# don't add 'my' in front of below because the variable is declared in the caller.
our $our_cfg = {
   resources => {
      test_driver => {
         method => sub { return {dummy_driver=>1} },
         cfg => {
         },
         # enabled => 1,   # default is enabled.
      },
   },


   show_progress => 1,

   # position_args = required args.
   # they will be inserted into $opt hash to pass forward.
   # NOTE:
   #   make sure keys not using the reserved words, eg
   #      b, batch, s, suite, ...
   position_args => [ qw(test_position_arg1 test_position_arg2) ],

   extra_args => {
      # this will create another two attr in $our_cfg
      #   extra_getopts
      #      this will feed into tpbatch script's GetOptions()
      #   extra_options
      #      this will store what tpbatch script's GetOptions() got from command line.
      #      then the data will be stored in $opt to pass forward. 
      # NOTE:
      #   make sure keys on both sides not using the reserved words, eg
      #      b, batch, s, suite, ...
      test_switch  => 'tw',       # -tw
      test_value   => 'to=s',     # -to hello
      test_array   => { spec=>'ta=i',  type=>'ARRAY', help=>'test array args' },
      test_hash    => { spec=>'th=s',  type=>'HASH',  help=>'test hash  args' },
   },

   pre_checks => [
      {
         check      => 'exists($ENV{HOME})',
         suggestion => 'run: export HTTPS_CA_DIR=/etc/ssl/certs',
      }
   ],

   usage_example => <<'END',

   linux1$ {{prog}} hello world s=tian -tw -to happy -ta 1 -ta 2 -th k1=1 -th k2=2 

END

   # all keys in keys, suits and aliases should be upper case
   # this way so that user can use case-insensitive keys on command line
   keys => {
      NAME  =>  undef, 
      ENTRY =>  undef, 
   },

   suits => {
      tian => {
         NAME => 'Tianhua Han',
         ENTRY => 'lca_tian',
      },

      editor => {
         NAME => 'LCA Editor Tester',
         ENTRY => 'lca_editor',
      },
   },

   aliases => {
      n => 'NAME',
      e => 'ENTRY',
   },
};

use TPSUP::LOCK qw(get_entry_by_key);

sub code {
   my ($all_cfg, $known, $opt) = @_;

   print "all_cfg = ", Dumper($all_cfg);
   print "opt = ",     Dumper($opt);
   print "known = ",   Dumper($known);

   my $verbose = $opt->{verbose};

   my $entry_key = $known->{ENTRY};
   my $entry = get_entry_by_key($entry_key);
   die "get_entry_by_key($entry_key}) failed" if !$entry;

   my $username = $entry->{user};
   my $password = $entry->{decoded};

   my $driver = $all_cfg->{resources}->{test_driver}->{driver};

   print "got driver = ", Dumper($driver);
}

sub post_batch {
   my ($all_cfg, $opt) = @_;

   print "this is from post_batch\n";
}
