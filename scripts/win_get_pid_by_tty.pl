#!/usr/bin/env perl

use warnings;
use strict;
use Data::Dumper;
$Data::Dumper::Sortkeys = 1;    # this sorts the Dumper output!
$Data::Dumper::Terse    = 1;

use Getopt::Long;
use Carp;
use File::Basename;

# try not use any TPSUP:: modules as if they break, this script breaks too.

my $prog = $0;
$prog =~ s:.*/::;

sub usage {
   my ($message) = @_;

   print "$message\n" if $message;

   print STDERR << "END";
usage:

   $prog tty
   $prog current
   
   on windows, find the pid of the process that is using the tty.

   tty can be short tty name, eg, pty0, pts/0, or full path, eg, /dev/pty0, /dev/pts/0.

   'current' is a special keyword, which means the current tty.

   -v               verbose mode
   -v -v            more verbose mode

examples:

   $prog        pty0
   $prog        /dev/pty0
   $prog        current

END

   exit 1;
}

my $verbose = 0;

GetOptions( 'v|verbose+' => \$verbose, ) || usage("cannot parse command line: $!");

usage("wrong number of args") if @ARGV != 1;

my ($tty) = @ARGV;

sub full2short {
   my ($full) = @_;

   # /dev/pts/0 -> pts/0
   $full =~ s:^/dev/::;

   return $full;
}

my $full_tty;
my $short_tty;

if ( $tty eq 'current' ) {
   $full_tty = `tty`;
   chomp $full_tty;
   $short_tty = full2short($full_tty);
} elsif ( $tty =~ m:^/dev/: ) {
   $full_tty  = $tty;
   $short_tty = full2short($full_tty);
} else {
   $short_tty = $tty;
   $full_tty  = "/dev/$tty";
}

if ($verbose) {
   print STDERR "full_tty: $full_tty\n";
   print STDERR "short_tty: $short_tty\n";
}

# find the pid of the mintty process that is using this tty
# note: cygwin's 'ps' comamnd does not support -t option.
# so we have to use "ps -ef" and then parse it.
#
# tian@tianpc2:/cygdrive/c/Users/tian$ ps -ef
#  tian    1068    1067 pty0       Jun 12 -bash
#  tian    2392    1068 pty0     17:10:28 ps -ef
my $cmd = "ps -ef";
if ($verbose) {
   print STDERR "running: $cmd\n";
}

my $ps_output = `$cmd`;

if ($verbose) {
   print STDERR "ps output:\n$ps_output\n";
}

my @lines    = split /\n/, $ps_output;
my $pid2ppid = {};

for my $line (@lines) {
   # my @a = split /\s+/, $line;
   # cannot use split as the ps output may contain spaces on the front.
   # (?:...) is a non-capturing group, so we can use it to match the spaces at the beginning.
   my @a = ( $line =~ m/^\s*(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)(?:\s+(\S+))?/ );

   if ( $verbose > 1 ) {
      print STDERR "line: $line\n";
      print STDERR "a: ", Dumper( \@a );
   }

   # the command is either -bash, /usr/bin/bash
   if ( $a[5] !~ m:^(-bash|/usr/bin/bash):
      && ( !$a[6] || $a[6] !~ m:^(-bash|/usr/bin/bash): ) )
   {
      next;    # not a bash process, skip it
   }

   $verbose > 1 and print STDERR "found a bash process: $line\n";

   my $pid    = $a[1];
   my $ppid   = $a[2];
   my $ps_tty = $a[3];

   next if $ps_tty ne $short_tty;

   if ( $verbose > 1 ) {
      print STDERR "found pid=$pid, ppid=$ppid, tty=$tty\n";
   }

   $pid2ppid->{$pid} = $ppid;
}

$verbose and print STDERR "pid2ppid: ", Dumper($pid2ppid);

# find the pid whose ppid is not in the hash.
for my $pid ( keys %$pid2ppid ) {
   my $ppid = $pid2ppid->{$pid};

   if ( !exists $pid2ppid->{$ppid} ) {
      print "$pid\n";
      exit 0;
   }
}

# if we reach here, it means we cannot find the pid.
$verbose and print STDERR "cannot find the pid for tty $full_tty\n";
exit 1;
