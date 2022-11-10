#!/usr/bin/perl
# https://perldoc.perl.org/perlperf.html
#
# dereference is actually slower, but only slightly, while making the code more readable
#
# tian@linux1:/home/tian/github/tpsup/scripts$ ./benchmark_test.pl
# Benchmark: timing 10000000 iterations of dereference, direct...
# dereference:  6 wallclock secs ( 5.44 usr +  0.00 sys =  5.44 CPU) @ 1838235.29/s (n=10000000)
#      direct:  3 wallclock secs ( 3.42 usr +  0.00 sys =  3.42 CPU) @ 2923976.61/s (n=10000000)
#
#  Benchmark: timing 10000000 iterations of sr, tr...
#        sr: 11 wallclock secs (12.35 usr +  0.00 sys = 12.35 CPU) @ 809716.60/s (n=10000000)
#        tr:  1 wallclock secs ( 1.81 usr +  0.00 sys =  1.81 CPU) @ 5524861.88/s (n=10000000)


use strict;
use warnings;

use Benchmark;

my $ref = {
        'ref'   => {
            _myscore    => '100 + 1',
            _yourscore  => '102 - 1',
        },
};

timethese(10000000, {
        'direct'       => sub {
          my $x = $ref->{ref}->{_myscore} . $ref->{ref}->{_yourscore} ;
        },

        'dereference'  => sub {
            my $ref  = $ref->{ref};
            my $myscore = $ref->{_myscore};
            my $yourscore = $ref->{_yourscore};
            my $x = $myscore . $yourscore;
        },
});

my $STR = "$$-this and that";

timethese( 10000000, {
   'sr'  => sub { my $str = $STR; $str =~ s/[aeiou]/x/g; return $str; },
   'tr'  => sub { my $str = $STR; $str =~ tr/aeiou/xxxxx/; return $str; },
});
