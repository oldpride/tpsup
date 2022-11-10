#!/usr/bin/perl

use strict;
use warnings;

use File::Basename;
use lib dirname (__FILE__);
use test_eval_return2 qw($we_return);

our $we_return;

sub f1 {
   my $i = 0;
   $we_return = 0;

   while (1) {
      print "round $i\n";
      print "we_return=$we_return\n";

      return if $we_return;

      if ($i == 1) {
         print "we return\n";
         test_eval_return2::eval_sub2('$we_return=1');
      }
   
      $i++;
      sleep 2;
   }
}

f1();
