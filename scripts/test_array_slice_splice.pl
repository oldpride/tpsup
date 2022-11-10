#!/usr/bin/perl

use strict;
use warnings;

my @a = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9);

my @exps = (
   '@a',
   '@a[0..$#a-1]',
   '@a[1..$#a-1]',
   '@a[1..3]',
   '@a[8..$#a]',
   '@a[8..20]',
   '@a[15..20]',
   '@a[0..$#a-15]',
);

print "\n!!! you will see 'uninitialized value' because slicer will insert undef value when out of range!!!\n\n";

for my $e (@exps) {
   printf("%-20s", "exp=$e: "); 
   eval('print join(",", ' . $e . '), "\n";');
}
print "\n";
