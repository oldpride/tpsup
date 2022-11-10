#!/usr/bin/perl

# test_assign_func.pl

use strict;
use warnings;

sub echo {
   my ($string) = @_;
   print "from echo: $string\n\n";
}

my $myprint = \&echo;
$myprint->("hello");

my $type = ref $myprint;
print "type=$type\n";

# the above didn't work
# https://stackoverflow.com/questions/69226416/in-perl-how-to-assign-the-print-function-to-a-variable/69226605#69226605

$myprint = \&print;
$myprint->("world");

