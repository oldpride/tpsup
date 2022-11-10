#!/usr/bin/perl
use strict;
use warnings;

#use Capture::Tiny qw(capture);       # this works
# this is the same as
# BEGIN {
#       require Capture::Tiny;
#       Capture::Tiny->import(qw(capture));
# }

require Capture::Tiny;    
# this will get the result but also triggers an error
#   Can't use string ("0") as a subroutine ref while "strict refs" in use at /usr/local/share/perl/5.26.1/Capture/Tiny.pm line 382.

my ($stdout, $stderr, $exit) = Capture::Tiny::capture {
  system("echo", "hello" );
};
print "stdout = $stdout\n";



