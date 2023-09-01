#!/usr/bin/perl

# TODO: not working yet: not printing debug messaage like the shell command

use warnings;
use strict;
use Data::Dumper;
use Getopt::Long;
use strict;
use Carp;

use IO::Socket::SSL qw(debug4);
# this is the same as 
# perl -MIO::Socket::SSL=debug4 prog.pl


use TPSUP::MECHANIZE;

my $prog = $0; $prog =~ s:.*/::;

my $number_of_retries = 1;
my $retry_interval = 3;

sub usage {
   my ($message) = @_;

   print "$message\n" if $message;

   print <<"END";
usage:
   This script is to debug Mechanize connection.
   $prog url 

   -v                     verbose mode.

examples:

   $prog "https://fundresearch.fidelity.com/mutual-funds/fees-and-prices/316343201"

END
   exit 1;
}

my $verbose;

GetOptions(
   'v|verbose'=>      \$verbose,
) || usage("cannot parse command line: $!");

usage("wrong number of args") if @ARGV != 1;

my ($url) = @ARGV;

my $mech = TPSUP::MECHANIZE::get_mech();

print "going to $url\n";

$mech->get($url);
