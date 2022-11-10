package TPSUP::ENV;

use strict;
use warnings;
use base qw( Exporter );
our @EXPORT_OK = qw(
   get_uname
);


use Carp;
$SIG{ __DIE__ } = \&Carp::confess; # this stack-trace on all fatal error !!!

use Data::Dumper;
$Data::Dumper::Terse = 1;     # print without "$VAR1="
$Data::Dumper::Sortkeys = 1;  # this sorts the Dumper output!

sub get_uname {
   my ($opt) = @_;

   my $ret;
   my $uname = `uname -a`; chomp $uname;
   my @ua = split /\s/, $uname;

   if ($ua[0] =~ /Linux/) {
      # Linux linux1 4.15.0-112-generic #113-Ubuntu SMP Thu Jul 9 23:41:39 
      #   UTC 2020 x86_64 x86_64 x86_64 GNU/Linux

      $ret->{OS_TYPE} = "Linux";
      @{$ret}{qw(OS_MAJOR OS_MINOR OS_PATCH)} = split /[.]/, $ua[2];
   } elsif ($ua[0] =~ /CYGWIN/ || $uname =~ /Mysys/) {
      # CYGWIN_NT-10.0 tianpc 3.1.7(0.340/5/3) 2020-08-22 17:48 x86_64 Cygwin
      $ret->{OS_TYPE} = "Windows";

      my ($junk1, $version, $junk2) = split /-/, $ua[0];
      @{$ret}{qw(OS_MAJOR OS_MINOR)} = split /[.]/, $version;

      if ($uname =~ /Mysys/) {
         $ret->{OS_TERM} = "GitBash";
      } else {
         $ret->{OS_TERM} = "Cygwin";
      }
   } else {
      $ret->{OS_TYPE} = "Unknown";
   }

   return $ret;
}

sub main {
   print "get_uname() = ", Dumper(get_uname());
}

main() unless caller();

1
