package test_eval_scope;

use strict;
use warnings;

my %h = (a=>'b');

sub f1 {
   eval 'print %h, "\n"';

   # print %h, "\n";   # this would work
   # my $dummy = \%h;  # adding this would also work
}

1
