#!/usr/bin/env perl

use warnings;
use strict;
use Data::Dumper;
use Getopt::Long;
use Carp;


my $h1 = {a=>1, b=>2,};
my $h2 = {b=>3, c=>4,};
my $h3;
my $h4;

   $h3 = {%$h1, %$h2};
  %$h4 = (%$h1, %$h2);
my %h5 = (%$h1, %$h2);


print "h3=", Dumper($h3);
print "h4=", Dumper($h4);
print "h5=", Dumper(%h5);
