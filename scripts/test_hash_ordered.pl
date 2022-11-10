#!/usr/bin/env perl

use warnings;
use strict;
use Data::Dumper;
use Getopt::Long;
use Carp;


my $h1 = [a=>1, b=>2, c=>3];

print "h1=", Dumper($h1);

while (@$h1) {
   my $k = shift @$h1;
   my $v = shift @$h1;

   print "$k = $v\n";

}

# the following failed to compile: Experimental shift on scalar is now forbidden
# my $h2 = {a=>1, b=>2, c=>3};
# 
# print "h2=", Dumper($h2);
# 
# while (%$h2) {
#    my $k = shift %$h2;
#    my $v = shift %$h2;
# 
#    print "$k = $v\n";
# 
# }
# 
