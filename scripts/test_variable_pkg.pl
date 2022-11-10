#!/usr/bin/perl

# https://stackoverflow.com/questions/2648517/how-can-i-use-a-variable-as-a-module-name-in-perl
# https://stackoverflow.com/questions/25486449/check-if-subroutine-exists-in-perl

use strict;
use warnings;

use Carp;
$SIG{ __DIE__ } = \&Carp::confess; # this stack-trace on all fatal error !!!


my $pkg = "TPSUP::DATE";

eval "require $pkg";


# best way to call a pkg sub is to assign it to a variable.
# use \ when assign to a variable.
my $f = \&{$pkg.'::get_tradeday'};
print "previous trade day = ", $f->(-1), "\n";

# when test existence, don't add \
if (exists &{$pkg.'::get_tradeday'}) {
   print "${pkg}::get_tradedays exists\n";
}

