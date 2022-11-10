#!/usr/bin/perl

use strict;
use warnings;

sub sub1 {

   my $v = "set by sub1";

   sub sub2 {
      print "in sub2 v=$v\n";
      $v = "set by sub2"; 
      print "in sub2 v=$v\n";
   }

   print "in sub1 v=$v\n";
   sub2();
   print "in sub1 v=$v\n";
}

sub1();
print "-----------------\n";
sub1();


__END__
output

Variable "$v" will not stay shared at /home/tian/sitebase/github/tpsup/scripts/test_sub_in_sub.pl line 11.
in sub1 v=set by sub1
in sub2 v=set by sub1
in sub2 v=set by sub2
in sub1 v=set by sub2
-----------------
in sub1 v=set by sub1
in sub2 v=set by sub2
in sub2 v=set by sub2
in sub1 v=set by sub1

note the second run had different results

to fix, see
   https://stackoverflow.com/questions/25399728/perl-variable-will-not-stay-shared

