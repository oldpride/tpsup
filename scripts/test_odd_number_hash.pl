#!/usr/bin/perl

use warnings;
use strict;
use Data::Dumper;

print <<"EOF";

we will see: Odd number of elements in anonymous hash at ...

search for the undef, you will locate the unpaired

EOF


my $h = {
   a=>1,
   b=>{a=>1, 
       'eh',
      },
   c=>1,
};

print Dumper($h);

