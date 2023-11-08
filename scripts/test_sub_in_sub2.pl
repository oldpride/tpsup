#!/usr/bin/perl

use strict;
use warnings;

sub sub1 {

   my $v = "set by sub1";

   my $sub2 = sub {
      print "in sub2 v=$v\n";
      $v = "set by sub2"; 
      print "in sub2 v=$v\n";
   };

   print "in sub1 v=$v\n";
   $sub2->();
   print "in sub1 v=$v\n";
}

sub1();
print "-----------------\n";
sub1();


# https://stackoverflow.com/questions/25399728/perl-variable-will-not-stay-shared

