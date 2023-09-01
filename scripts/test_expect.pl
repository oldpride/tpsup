#!/usr/bin/perl

use Expect;
use warnings;
use strict;
use Data::Dumper;
use Getopt::Long;
use strict;
use TPSUP::LOCK qw(get_entry_by_key);

my $prog = $0; $prog =~ s:.*/::;

my $yyyymmdd = `date +%Y%m%d`; chomp $yyyymmdd;
my $HHMMSS   = `date +%H%M%S`; chomp $HHMMSS;

sub usage {
   my ($message) = @_;
   print "$message\n" if $message;

   print <<"END";
usage:

   $prog dryrun
   $prog get

   -v verbose mode.

example:

   $prog get
   $prog  dryrun

END

   exit 1;
}

my $verbose;

GetOptions (
   "v" => \$verbose,
) or usage("failed parsing command line arguments: $!\n");

usage("wrong number of args") if @ARGV != 1;

my $sftp_user = "sftpuser";
my $sftp_host = "sftphost.abc.com";

my $key = "$sftp_user\@$sftp_host";

my $entry = get_entry_by_key($key);
my $pw = $entry->{decoded};

die "cannot figure out password key=$key" if !$pw;

my $cmd = "sftp $sftp_user\@$sftp_host";

print "cmd = $cmd\n";

my $exp = Expect->spawn($cmd) or die "Cannot spawn $cmd: $!\n";

my_expect("^Password:", 3);

$exp->send("$pw\n");

$exp->log_user(1) ;

my_expect("sftp>", 3) ;

$exp->send("get -p /remotedir/remote_file.txt");

sleep 3;

my_expect("Fetching", 3);

#################################
# subs
#################################

sub my_expect {
   my ($pattern, $timeout) = @_;

   my ($matched_pattern_position, $error, $successfully_matching_string,
       $before_match, $after_match) = $exp->expect($timeout, [ qr/$pattern/ ]);
       
   if ($verbose) {
      print <<"EOF"

pattern='$pattern'

before_match='$before_match'

after_match='$after_match'

EOF
   }

   if (!defined $matched_pattern_position) {
      my $message = "cannot match pattern='$pattern' in $timeout seconds.";
      print $message;
      exit 1;
   }
}
