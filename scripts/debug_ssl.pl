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


my $prog = $0; $prog =~ s:.*/::;

sub usage {
   my ($message) = @_;

   print "$message\n" if $message;

   print <<"END";
usage:
   This script is to debug Mechanize connection.

   $prog module url 

   'module' can be mech (Mecchanize), lwp

   -v                     verbose mode.

examples:

   $prog mech "https://fundresearch.fidelity.com/mutual-funds/fees-and-prices/316343201"
   $prog lwp  "https://fundresearch.fidelity.com/mutual-funds/fees-and-prices/316343201"

END
   exit 1;
}

my $verbose;

GetOptions(
   'v|verbose'=>      \$verbose,
) || usage("cannot parse command line: $!");

usage("wrong number of args") if @ARGV != 2;

my ($mod, $url) = @ARGV;

if ($mod eq 'mech') {
   use TPSUP::MECHANIZE;
   my $mech = TPSUP::MECHANIZE::get_mech();

   print "going to $url\n";

   $mech->get($url);
} elsif ($mod eq 'lwp') {
   use LWP::UserAgent;
   use HTTP::Request;
   my $ua = LWP::UserAgent->new;
   my $req = HTTP::Request->new( GET => $url);
   my $response = $ua->request($req);
   print $response->status_line . "\n";
}
