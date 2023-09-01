#!/usr/bin/perl

use strict;
use warnings;

 
# eval 'return' from a subroutine doesn't go back to the caller but actually does nothing
#    because eval allows optional 'return' statement.
# https://perldoc.perl.org/functions/eval
#    "a return statement may also be used, just as with subroutines"

sub f1 {
   my $i = 0;
   while (1) {
      print "round $i\n";

      if ($i == 1) {
         print "we will return\n";
         eval 'return';
         eval 'last';      # last works
         # eval 'exit';    # exit works
      }
   
      $i++;
      sleep 2;
   }
}

f1();
