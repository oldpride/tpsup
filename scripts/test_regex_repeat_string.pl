#!/usr/bin/perl

use strict;
use warnings;
use Data::Dumper;
$Data::Dumper::Sortkeys = 1;  # this sorts the Dumper output!
$Data::Dumper::Terse = 1;     # print without "$VAR1="

my @strings = (
    "this has 0 string: ",
    "this has 1 string: abc",
    "this has 2 repeat strings: abc abc",
    "this has 3 repeat strings: abc abc abc",
);

my @patterns = (
   'this has .*:(?: (abc)){0,2}',
   'this has .*:( abc){0,2}',
   'this has .*:( abc{0,2})',
   'this has .*:((?: abc){0,2})',   # this works
);

for my $s (@strings) {
   for my $p (@patterns) {
      print "\n";
      print "string=$s\n";
      print "pattern=$p\n";

      my @captures = ($s =~ /$p/sg);
      if (@captures) {
         print "matched. captures=" . Dumper(\@captures); 
      } else {
         print "didn't match\n";
      }
   }
}


